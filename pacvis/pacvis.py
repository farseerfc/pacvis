#!/usr/bin/env python

import math
import random
import json
from itertools import groupby
from types import SimpleNamespace

import pyalpm
import tornado.ioloop
import tornado.web

from .console import start_message, append_message, print_message


class PkgInfo:

    @classmethod
    def cinit(cls):
        cls.localdb = pyalpm.Handle("/", "/var/lib/pacman").get_localdb()
        cls.packages = cls.localdb.pkgcache
        cls.all_pkgs = {}
        cls.groups = {}

    def __init__(self, name):
        self.name = name
        self.pkg = PkgInfo.localdb.get_pkg(name)
        self.deps = [PkgInfo.resolve_dependency(dep).name
                     for dep in self.pkg.depends]
        self.requiredby = self.pkg.compute_requiredby()
        self.optdeps = []
        for dep in self.pkg.optdepends:
            depname = dep.split(":")[0]
            resolved = PkgInfo.resolve_dependency(depname)
            if resolved is not None:
                self.optdeps.append(resolved.name)
        self.level = 1
        self.circledeps = []
        self.explicit = self.pkg.reason == 0
        self.isize = self.pkg.isize
        self.desc = self.pkg.desc
        self.version = self.pkg.version
        PkgInfo.all_pkgs[name] = self
        self.groups = self.pkg.groups
        for grp in self.groups:
            if grp in PkgInfo.groups:
                PkgInfo.groups[grp].add_pkg(self.name)
            else:
                GroupInfo(grp)
                PkgInfo.groups[grp].add_pkg(self.name)

    @classmethod
    def resolve_dependency(cls, dep):
        pkg = cls.localdb.get_pkg(dep)
        if pkg is None:
            pkg = pyalpm.find_satisfier(cls.packages, dep)
        return pkg

    @classmethod
    def get(cls, pkg):
        return cls.all_pkgs[pkg]

    @classmethod
    def find_all(cls):
        for pkg in cls.packages:
            PkgInfo(pkg.name)
        return cls.all_pkgs

    @classmethod
    def find_circles(cls):
        """ https://zh.wikipedia.org/wiki/Tarjan%E7%AE%97%E6%B3%95 """
        stack = list()
        indexes = dict()
        lowlinks = dict()
        index = 0

        def strongconnect(pkg):
            nonlocal stack, indexes, lowlinks, index
            indexes[pkg] = index
            lowlinks[pkg] = index
            index += 1
            stack.append(pkg)
            for dep in cls.get(pkg).deps:
                if dep not in indexes:
                    strongconnect(dep)
                    lowlinks[pkg] = min(lowlinks[pkg], lowlinks[dep])
                elif dep in stack:
                    lowlinks[pkg] = min(lowlinks[pkg], indexes[dep])
            if lowlinks[pkg] == indexes[pkg]:
                cirdeps = []
                while True:
                    w = stack.pop()
                    cirdeps.append(w)
                    if (w == pkg):
                        break
                cls.get(pkg).circledeps = cirdeps

        for pkg in cls.all_pkgs:
            if pkg not in indexes:
                strongconnect(pkg)

    @classmethod
    def top_down_sort(cls, usemagic):
        remain_pkgs = {x for x in cls.all_pkgs}
        start_message("Sorting ")
        while len(remain_pkgs) > 0:
            pkg = remain_pkgs.pop()
            origin_level = cls.get(pkg).level
            append_message("%s %d (remaining %d)" % (pkg,
                                                     origin_level,
                                                     len(remain_pkgs)))
            if len(cls.get(pkg).deps) == 0:
                if len(cls.get(pkg).requiredby) == 0:
                    cls.get(pkg).level = 0
                continue
            max_level = max(cls.get(x).level for x in cls.get(pkg).deps) + 1
            if usemagic:
                # below is magic
                new_level = max_level + int(math.log(1 +
                                                     len(cls.get(pkg).deps) +
                                                     len(cls.get(pkg).requiredby)))
            else:
                new_level = max_level  # we may not need magic at all
            if new_level != origin_level:
                cls.get(pkg).level = new_level
                remain_pkgs.update(set(cls.get(pkg).requiredby)
                                   .difference(cls.get(pkg).circledeps))

    @classmethod
    def buttom_up_sort(cls):
        remain_pkgs = {x for x in cls.all_pkgs}
        start_message("Resorting ")
        while len(remain_pkgs) > 0:
            pkg = remain_pkgs.pop()
            origin_level = cls.get(pkg).level
            append_message("%s %d (remaining %d)" % (pkg,
                                                     origin_level,
                                                     len(remain_pkgs)))
            if len(cls.get(pkg).requiredby) == 0:
                if len(cls.get(pkg).deps) == 0:
                    cls.get(pkg).level = 0
                continue
            min_level = min(cls.get(x).level for x in cls.get(pkg).requiredby)
            new_level = min_level - 1
            if new_level > origin_level:
                cls.get(pkg).level = new_level
                remain_pkgs.update(set(cls.get(pkg).deps)
                                   .difference(cls.get(pkg).circledeps))

    @classmethod
    def minimize_levels(cls):
        start_message("Minimizing levels ... ")
        pkgs = list(sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level))
        nextlevel = 0
        for key, group in groupby(pkgs, key=lambda x: x.level):
            for pkg in group:
                pkg.level = nextlevel
            nextlevel += 1
        append_message("max available level: %d" % nextlevel)

    @classmethod
    def topology_sort(cls, usemagic, aligntop):
        cls.top_down_sort(usemagic)
        cls.buttom_up_sort()
        if aligntop:
            cls.top_down_sort(usemagic) # do top_down_sort again to align to top
        cls.minimize_levels()

    @classmethod
    def calcCSize(cls, pkg):
        removing_pkg = set()

        def remove_pkg(pkgname):
            nonlocal removing_pkg
            removing_pkg.add(pkgname)
            for dep in cls.all_pkgs[pkgname].requiredby:
                if dep not in removing_pkg:
                    remove_pkg(dep)

        remove_pkg(pkg.name)
        pkg.csize = sum(cls.all_pkgs[pkg].isize for pkg in removing_pkg)
        append_message("csize %s: %d" % (pkg.name, pkg.csize))
        return pkg.csize

    @classmethod
    def calcCsSize(cls, pkg):
        removing_pkg = set()
        analyzing_pkg = set()

        def remove_pkg(pkgname):
            nonlocal removing_pkg
            removing_pkg.add(pkgname)
            for dep in cls.all_pkgs[pkgname].deps:
                if not cls.all_pkgs[dep].explicit:
                    analyzing_pkg.add(dep)
            for dep in cls.all_pkgs[pkgname].requiredby:
                if dep not in removing_pkg:
                    remove_pkg(dep)

        remove_pkg(pkg.name)
        while len(analyzing_pkg) > 0:
            apkg = cls.all_pkgs[analyzing_pkg.pop()]
            if apkg.name in removing_pkg:
                continue
            if all(dep in removing_pkg for dep in apkg.requiredby):
                remove_pkg(apkg.name)
        pkg.cssize = sum(cls.all_pkgs[pkg].isize for pkg in removing_pkg)
        append_message("cssize %s: %d" % (pkg.name, pkg.cssize))
        return pkg.cssize

    @classmethod
    def calcSizes(cls):
        start_message("Calculating csize ... ")
        maxCSize = max(cls.calcCSize(pkg) for pkg in cls.all_pkgs.values())
        print_message("Max cSize: " + str(maxCSize))
        start_message("Calculating cssize ... ")
        maxCsSize = max(cls.calcCsSize(pkg) for pkg in cls.all_pkgs.values())
        print_message("Max csSize: " + str(maxCsSize))


class GroupInfo (PkgInfo):
    def __init__(self, name):
        self.name = name
        self.deps = []
        self.requiredby = []
        self.optdeps = []
        self.level = 1
        self.circledeps = []
        self.explicit = True
        self.isize = 0
        self.desc = name + " package group"
        self.version = ""
        PkgInfo.groups[name] = self
        PkgInfo.all_pkgs[name] = self

    def add_pkg(self, pkgname):
        self.deps.append(pkgname)
        PkgInfo.all_pkgs[pkgname].requiredby.append(self.name)


def test_circle_detection():
    start_message("find all packages...")
    PkgInfo.find_all()
    append_message("done")
    start_message("find all dependency circles...")
    PkgInfo.find_circles()
    append_message("done")
    for name, pkg in PkgInfo.all_pkgs.items():
        if len(pkg.circledeps) > 1:
            print_message("%s(%s): %s" %
                          (pkg.name, pkg.circledeps, ", ".join(pkg.deps)))
    PkgInfo.topology_sort()
    for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
        print("%s(%d): %s" % (pkg.name, pkg.level, ", ".join(pkg.deps)))


# Tornado entry
class MainHandler(tornado.web.RequestHandler):

    def parse_args(self, **kargs):
        result = {}
        for key in kargs:
            if type(kargs[key]) is int:
                result[key] = int(self.get_argument(key, str(kargs[key])))
            elif type(kargs[key]) is bool:
                result[key] = (self.get_argument(key, str(kargs[key])) != "False")
            else:
                result[key] = self.get_argument(key, str(kargs[key]))
            print_message("get arg %r: %r" %(key, result[key]))
        return result

    def get(self):
        print_message("\n"+ str(self.request))
        args = SimpleNamespace(**self.parse_args(
            maxlevel=1000,
            maxreqs=1000,
            usemagic=False,
            enablephysics=False,
            aligntop=False,
            disableallphysics=False,
            debugperformance=False))
        PkgInfo.cinit()
        start_message("Loading local database ...")
        PkgInfo.find_all()
        append_message("done")
        start_message("Finding all dependency circles ... ")
        PkgInfo.find_circles()
        append_message("done")
        PkgInfo.topology_sort(args.usemagic, args.aligntop)
        PkgInfo.calcSizes()

        start_message("Rendering ... ")

        nodes = []
        links = []

        nodes.append({"id": 0,
                      "label": "level 0 group",
                      "level": -1,
                      "shape": "triangleDown",
                      "isize": 0,
                      "csize": 0,
                      "cssize": 0,
                      "deps": "",
                      "reqs": "",
                      "optdeps": "",
                      "desc": "",
                      "version": "",
                      "group": "group"
                      })

        ids = 1
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
            append_message("%s" % pkg.name)
            pkg.id = ids
            ids += 1
            if pkg.level < args.maxlevel:
                group = "normal"
                if pkg.level == 0:
                    group = "standalone"
                elif type(pkg) is GroupInfo:
                    group = "group"
                elif pkg.explicit:
                    group = "explicit"
                nodes.append({"id": pkg.id,
                              "label": pkg.name,
                              "level": pkg.level,
                              "group": group,
                              "isize": pkg.isize,
                              "csize": pkg.csize,
                              "cssize": pkg.cssize,
                              "deps": ", ".join(pkg.deps),
                              "reqs": ", ".join(pkg.requiredby),
                              "optdeps": ", ".join(pkg.optdeps),
                              "desc": pkg.desc,
                              "version": pkg.version,
                              })
        ids = 0
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
            if pkg.level < args.maxlevel:
                if pkg.level == 0:
                    links.append({"id": ids,
                                  "from": pkg.id,
                                  "to": 0})
                    ids += 1
                for dep in pkg.deps:
                    if dep not in pkg.circledeps:
                        if len(PkgInfo.all_pkgs[dep].requiredby) < args.maxreqs:
                            links.append({"id": ids,
                                          "from": pkg.id,
                                          "to": PkgInfo.all_pkgs[dep].id})
                            ids += 1
                for dep in pkg.circledeps:
                    if (pkg.id != PkgInfo.all_pkgs[dep].id):
                        links.append({"id": ids,
                                      "to": pkg.id,
                                      "from": PkgInfo.all_pkgs[dep].id,
                                      "color": "rgb(255,0,0)"})
                        ids += 1
                for dep in pkg.optdeps:
                    if dep in PkgInfo.all_pkgs:
                        links.append({"id": ids,
                                      "from": pkg.id,
                                      "to": PkgInfo.all_pkgs[dep].id,
                                      "dashes": True,
                                      "color": "rgb(255,255,100)"})
                        ids += 1
        print_message("Writing HTML")
        self.render("templates/index.template.html",
                    nodes=json.dumps(nodes),
                    links=json.dumps(links),
                    options=args)


def make_app():
    import os
    return tornado.web.Application([
        (r"/", MainHandler),
        ], debug=True,
        static_path=os.path.join(os.path.dirname(__file__), "static"))

def main():
    app = make_app()
    app.listen(8888)
    print_message("Start PacVis at http://localhost:8888/")
    tornado.ioloop.IOLoop.current().start()

if __name__ == "__main__":
    main()

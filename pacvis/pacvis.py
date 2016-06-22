import math
import random
from itertools import groupby

import pyalpm
import tornado.ioloop
import tornado.web

from console import start_message, append_message, print_message


class PkgInfo:
    all_pkgs = {}
    localdb = pyalpm.Handle("/", "/var/lib/pacman").get_localdb()
    packages = localdb.pkgcache

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
        PkgInfo.all_pkgs[name] = self


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
    def topology_sort(cls):
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
            # below is magic
            new_level = max_level + int(math.log(1 +
                                                 len(cls.get(pkg).deps) +
                                                 len(cls.get(pkg).requiredby)))
            # new_level = max_level  # we may not need magic at all
            if new_level != origin_level:
                cls.get(pkg).level = new_level
                remain_pkgs.update(set(cls.get(pkg).requiredby)
                                   .difference(cls.get(pkg).circledeps))
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
        start_message("Minimizing levels ... ")
        pkgs = list(sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level))
        nextlevel = 0
        for key, group in groupby(pkgs, key=lambda x: x.level):
            for pkg in group:
                pkg.level = nextlevel
            nextlevel += 1
        append_message("max available level: %d" % nextlevel)

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
        while len(analyzing_pkg)>0:
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
    def get(self):
        maxlevel = int(self.get_argument("maxlevel", "1000"))
        maxreqs = int(self.get_argument("maxreqs", "30"))
        PkgInfo.all_pkgs = {}
        PkgInfo.localdb = pyalpm.Handle("/", "/var/lib/pacman").get_localdb()
        PkgInfo.packages = PkgInfo.localdb.pkgcache
        print_message("Max level: %d" % maxlevel)
        start_message("Loading local database ...")
        PkgInfo.find_all()
        append_message("done")
        start_message("Finding all dependency circles ... ")
        PkgInfo.find_circles()
        append_message("done")
        PkgInfo.topology_sort()
        PkgInfo.calcSizes()

        start_message("Rendering ... ")

        nodes = []
        links = []

        ids = 0
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
            append_message("%s" % pkg.name)
            pkg.id = ids
            ids += 1
            if pkg.level < maxlevel:
                group = "normal"
                if pkg.level == 0:
                    group = "standalone"
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
                              "desc": pkg.pkg.desc,
                              "version": pkg.pkg.version,
                              })
        ids = 0
        circlelinks = []
        optlinks = []
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
            if pkg.level < maxlevel:
                for dep in pkg.deps:
                    if dep not in pkg.circledeps:
                        if len(PkgInfo.all_pkgs[dep].requiredby) < maxreqs:
                            links.append({"id": ids,
                                          "from": pkg.id,
                                          "to": PkgInfo.all_pkgs[dep].id})
                            ids += 1
                for dep in pkg.circledeps:
                    if (pkg.id != PkgInfo.all_pkgs[dep].id):
                        circlelinks.append({"id": ids,
                                            "to": pkg.id,
                                            "from": PkgInfo.all_pkgs[dep].id})
                        ids += 1
                for dep in pkg.optdeps:
                    if dep in PkgInfo.all_pkgs:
                        optlinks.append({"id": ids,
                                         "from": pkg.id,
                                         "to": PkgInfo.all_pkgs[dep].id})
                        ids += 1
        print_message("Wrting HTML")
        self.render("templates/index.template.html",
                    nodes=nodes,
                    links=links,
                    circlelinks=circlelinks,
                    optlinks=optlinks,
                    options={"maxlevel" : maxlevel,
                             "maxreqs" : maxreqs})


def make_app():
    import os
    return tornado.web.Application([
        (r"/", MainHandler),
        ], debug=True,
        static_path=os.path.join(os.path.dirname(__file__), "static"))

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    print_message("Start PacVis at http://localhost:8888/")
    tornado.ioloop.IOLoop.current().start()

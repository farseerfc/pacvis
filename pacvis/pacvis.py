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
        self.level = 1
        self.circledeps = []
        self.explicit = self.pkg.reason == 0
        self.isize = self.pkg.isize
        PkgInfo.all_pkgs[name] = self

    def size(self):
        return self.isize

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
        MAX_LEVEL = int(self.get_argument("maxlevel", "1000"))
        PkgInfo.all_pkgs = {}
        PkgInfo.localdb = pyalpm.Handle("/", "/var/lib/pacman").get_localdb()
        PkgInfo.packages = PkgInfo.localdb.pkgcache
        print_message("Max level: %d" % MAX_LEVEL)
        start_message("Loading local database ...")
        PkgInfo.find_all()
        append_message("done")
        start_message("Finding all dependency circles ... ")
        PkgInfo.find_circles()
        append_message("done")
        PkgInfo.topology_sort()

        print_message("Rendering into HTML template")

        nodes = []
        links = []

        ids = 0
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
            pkg.id = ids
            ids += 1
            if pkg.level < MAX_LEVEL:
                group = "normal"
                if pkg.level == 0:
                    group = "standalone"
                elif pkg.explicit:
                    group = "explicit"
                nodes.append({"id": pkg.id,
                              "label": pkg.name,
                              "level": pkg.level,
                              "value": math.log(pkg.size()+1)*2,
                              "group": group,
                              "isize": pkg.size(),
                              "deps": ", ".join(pkg.deps),
                              "reqs": ", ".join(pkg.requiredby),
                              })
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x: x.level):
            if pkg.level < MAX_LEVEL:
                for dep in pkg.deps:
                    links.append({"from": pkg.id,
                                  "to": PkgInfo.all_pkgs[dep].id})

        self.render("templates/index.template.html", nodes=nodes, links=links)


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

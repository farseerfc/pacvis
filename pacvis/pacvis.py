import math
import random

import pyalpm
import tornado.ioloop
import tornado.web

from console import start_message, append_message, print_message

handle = pyalpm.Handle("/","/var/lib/pacman")
localdb = handle.get_localdb()
packages = localdb.pkgcache

consolidate_threshold = 3

def resolve_dependency(dep):
    pkg = localdb.get_pkg(dep)
    if pkg is None:
        pkg = pyalpm.find_satisfier(packages, dep)
    return pkg


class PkgInfo:
    all_pkgs = {}

    def __init__(self, name):
        self.name = name
        self.pkg = localdb.get_pkg(name)
        self.deps = [resolve_dependency(dep).name for dep in self.pkg.depends]
        self.requiredby = self.pkg.compute_requiredby()
        self.level = 1
        self.circledeps = []
        self.explicit = self.pkg.reason == 0
        self.isize = self.pkg.isize
        PkgInfo.all_pkgs[name] = self

    def info(self):
        return "%s(%d) depends:[%s] required-by:[%s]" % (
            self.name,
            self.level,
            ", ".join(self.deps),
            ", ".join(self.requiredby))

    def size(self):
        return self.isize

    @classmethod
    def get(cls, pkg):
        return cls.all_pkgs[pkg]

    @classmethod
    def find_all(cls):
        for pkg in packages:
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
    def consolidate(cls):
        depmap = {}
        for name,pkg in cls.all_pkgs.items():
            deps = tuple(sorted(pkg.deps))
            reqs = tuple(sorted(pkg.requiredby))
            key = (deps, reqs)
            if key in depmap:
                depmap[key].append(pkg)
            else:
                depmap[key] = [pkg]
        start_message("Consolidating ")
        for key,pkgs in depmap.items():
            if len(pkgs) > consolidate_threshold:
                consolidated = ConsolidatePkg(pkgs)
                for pkg in pkgs:
                    append_message("remove "+pkg.name)
                    cls.all_pkgs.pop(pkg.name)
                    for dep in consolidated.deps:
                        if pkg.name in cls.all_pkgs[dep].requiredby:
                            cls.all_pkgs[dep].requiredby.remove(pkg.name)
                    for dep in consolidated.requiredby:
                        if pkg.name in cls.all_pkgs[dep].deps:
                            cls.all_pkgs[dep].deps.remove(pkg.name)
                cls.all_pkgs[consolidated.name] = consolidated
                for dep in consolidated.deps:
                    cls.all_pkgs[dep].requiredby.append(consolidated.name)
                for dep in consolidated.requiredby:
                    cls.all_pkgs[dep].deps.append(consolidated.name)
                append_message("add " + consolidated.name)
                append_message("Packages: [%s] deps: [%s] reqs: [%s]" % (
                    ", ".join(pkg.name for pkg in pkgs),
                    ", ".join(consolidated.deps),
                    ", ".join(consolidated.requiredby)
                    ))
        append_message("... done")

    @classmethod
    def topology_sort(cls):
        remain_pkgs = {x for x in cls.all_pkgs}
        start_message("Sorting ")
        while len(remain_pkgs) > 0:
            pkg = remain_pkgs.pop()
            origin_level = cls.get(pkg).level
            append_message("%s %d (remaining %d)" % (pkg, origin_level, len(remain_pkgs)))
            if len(cls.get(pkg).deps) == 0:
                if len(cls.get(pkg).requiredby) == 0:
                    cls.get(pkg).level = 0
                continue
            max_level = max(cls.get(x).level for x in cls.get(pkg).deps)
            # below is magic
            new_level = max_level + int(math.log(1+ len(cls.get(pkg).deps) + len(cls.get(pkg).requiredby))) + 1
            if new_level != origin_level:
                cls.get(pkg).level = new_level
                remain_pkgs.update(set(cls.get(pkg).requiredby)
                    .difference(cls.get(pkg).circledeps))
        remain_pkgs = {x for x in cls.all_pkgs}
        start_message("Resorting ")
        while len(remain_pkgs) > 0:
            pkg = remain_pkgs.pop()
            origin_level = cls.get(pkg).level
            append_message("%s %d (remaining %d)" % (pkg, origin_level, len(remain_pkgs)))
            if len(cls.get(pkg).requiredby) == 0:
                if len(cls.get(pkg).deps) == 0:
                    cls.get(pkg).level = 0
                continue
            min_level = min(cls.get(x).level for x in cls.get(pkg).requiredby)
            # below is magic
            new_level = min_level - 1
            if new_level > origin_level:
                cls.get(pkg).level = new_level
                remain_pkgs.update(set(cls.get(pkg).deps)
                    .difference(cls.get(pkg).circledeps))


class ConsolidatePkg:
    def __init__ (self, pkgs):
        self.pkgs = pkgs
        self.deps = pkgs[0].deps
        self.requiredby = pkgs[0].requiredby
        self.circledeps = []
        self.level = 1
        self.name = "Group(%d, (%s), (%s))" % ( len(pkgs),
            ",".join(self.deps),
            ",".join(self.requiredby))

    def info(self):
        return "Group [%s] (%d) depends:[%s] required-by:[%s]" % (
            ", ".join(x.name for x in self.pkgs),
            self.level,
            ", ".join(self.deps),
            ", ".join(self.requiredby))

    def size(self):
        return sum(pkg.size() for pkg in self.pkgs)

def test_circle_detection():
    start_message("find all packages...")
    PkgInfo.find_all()
    append_message("done")
    start_message("find all dependency circles...")
    PkgInfo.find_circles()
    append_message("done")
    for name,pkg in PkgInfo.all_pkgs.items():
        if len(pkg.circledeps) > 1:
            print_message("%s(%s): %s" %
                (pkg.name, pkg.circledeps , ", ".join(pkg.deps)))
    PkgInfo.topology_sort()
    for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x:x.level):
        print("%s(%d): %s" % (pkg.name, pkg.level , ", ".join(pkg.deps)))

### Tornado entry

class MainHandler(tornado.web.RequestHandler):
    def get(self):
        MAX_LEVEL = int(self.get_argument("maxlevel", "30"))
        PkgInfo.all_pkgs = {}
        print_message("Max level: %d" % MAX_LEVEL)
        start_message("Loading local database...")
        PkgInfo.find_all()
        append_message("done")
        append_message("done")
        start_message("Finding all dependency circles...")
        PkgInfo.find_circles()
        append_message("done")
        PkgInfo.consolidate()
        PkgInfo.topology_sort()

        print_message("Rendering")

        nodes = []
        links = []

        ids = 0
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x:x.level):
            pkg.id = ids
            ids += 1
            if pkg.level < MAX_LEVEL:
                group = "normal"
                if isinstance(pkg, ConsolidatePkg):
                    group = "consolidated"
                elif pkg.level == 0 :
                    group =  "standalone"
                elif pkg.explicit:
                    group = "explicit"
                nodes.append({"id": pkg.id,
                              "label": pkg.name,
                              "level": pkg.level,
                              "title": pkg.info(),
                              "size": math.log(pkg.size()+1),
                              "group": group
                              })
        for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x:x.level):
            if pkg.level < MAX_LEVEL:
                for dep in pkg.deps:
                    links.append({"from": pkg.id, "to": PkgInfo.all_pkgs[dep].id})

        self.render("templates/index.template.html", nodes=nodes, links=links)

def make_app():
    import os
    return tornado.web.Application([
        (r"/", MainHandler),
    ], debug=True, static_path= os.path.join(os.path.dirname(__file__), "static"))

if __name__ == "__main__":
    app = make_app()
    app.listen(8888)
    tornado.ioloop.IOLoop.current().start()

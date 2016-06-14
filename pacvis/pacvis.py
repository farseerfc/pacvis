import math

import pyalpm
import jinja2


from console import start_message, append_message, print_message

handle = pyalpm.Handle("/","/var/lib/pacman")
localdb = handle.get_localdb()
packages = localdb.pkgcache


def resolve_dependency(dep):
    pkg = localdb.get_pkg(dep)
    if pkg is None:
        pkg = pyalpm.find_satisfier(packages, dep)
    return pkg


class PkgInfo:
    all_pkgs = {}

    def __init__(self, name):
        self._name = name
        self._pkg = localdb.get_pkg(name)
        self._deps = [resolve_dependency(dep).name for dep in self._pkg.depends]
        self._requiredby = self._pkg.compute_requiredby()
        self._level = 0
        self._circledeps = []
        PkgInfo.all_pkgs[name] = self

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
            for dep in cls.get(pkg)._deps:
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
                cls.get(pkg)._circledeps = cirdeps

        for pkg in cls.all_pkgs:
            if pkg not in indexes:
                strongconnect(pkg)


    @classmethod
    def topology_sort(cls):
        remain_pkgs = {x for x in cls.all_pkgs}
        start_message("Sorting ")
        while len(remain_pkgs) > 0:
            pkg = remain_pkgs.pop()
            origin_level = cls.get(pkg)._level
            append_message("%s %d (remaining %d)" % (pkg, origin_level, len(remain_pkgs)))
            if len(cls.get(pkg)._deps) == 0:
                continue
            max_level = max(cls.get(x)._level for x in cls.get(pkg)._deps)
            # below is magic
            new_level = max_level + math.log(1+ len(cls.get(pkg)._deps) + len(cls.get(pkg)._requiredby)) + 1
            if new_level != origin_level:
                cls.get(pkg)._level = new_level
                remain_pkgs.update(set(cls.get(pkg)._requiredby)
                    .difference(cls.get(pkg)._circledeps))


MAX_LEVEL = 40

def main():
    start_message("Loading local database...")
    PkgInfo.find_all()
    append_message("done")
    start_message("Finding all dependency circles...")
    PkgInfo.find_circles()
    append_message("done")
    PkgInfo.topology_sort()

    print_message("Writing to index.html")

    nodeps = []
    nodes = []
    links = []

    ids = 0
    for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x:x._level):
        pkg.id = ids
        ids += 1
        if len(pkg._deps) == 0 and len(pkg._requiredby) == 0:
            nodeps.append({"id": pkg.id, "label": pkg._name, "level": pkg._level})
        elif pkg._level < MAX_LEVEL:
            nodes.append({"id": pkg.id, "label": pkg._name, "level": pkg._level})
    for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x:x._level):
        if pkg._level < MAX_LEVEL:
            for dep in pkg._deps:
                links.append({"from": pkg.id, "to": PkgInfo.all_pkgs[dep].id})

    env = jinja2.Environment(loader=jinja2.PackageLoader('pacvis', 'templates'))
    template = env.get_template("index.template.html")
    with open("index.html", "w") as content:
        content.write(template.render(nodes=nodes, links=links, nodeps=nodeps))


def test():
    start_message("find all packages...")
    PkgInfo.find_all()
    append_message("done")
    start_message("find all dependency circles...")
    PkgInfo.find_circles()
    append_message("done")
    for name,pkg in PkgInfo.all_pkgs.items():
        if len(pkg._circledeps) > 1:
            print_message("%s(%s): %s" %
                (pkg._name, pkg._circledeps , ", ".join(pkg._deps)))
    PkgInfo.topology_sort()
    for pkg in sorted(PkgInfo.all_pkgs.values(), key=lambda x:x._level):
        print("%s(%d): %s" % (pkg._name, pkg._level , ", ".join(pkg._deps)))

if __name__ == '__main__':
    main()

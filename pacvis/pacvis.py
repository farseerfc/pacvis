#!/usr/bin/env python

import json
from types import SimpleNamespace
from argparse import ArgumentParser, ArgumentDefaultsHelpFormatter

import tornado.ioloop
import tornado.web

from .console import start_message, append_message, print_message
from .infos import DbInfo, PkgInfo, GroupInfo, VDepInfo


# Tornado entry
class MainHandler(tornado.web.RequestHandler):

    def parse_args(self, **kargs):
        result = {}
        for key in kargs:
            defvalue = str(kargs[key])
            if type(kargs[key]) is int:
                result[key] = int(self.get_argument(key, defvalue))
            elif type(kargs[key]) is bool:
                result[key] = self.get_argument(key, defvalue) != "False"
            else:
                result[key] = self.get_argument(key, defvalue)
            print_message("get arg %r: %r" % (key, result[key]))
        return result

    def get(self):
        print_message("\n" + str(self.request))
        args = SimpleNamespace(**self.parse_args(
            maxlevel=1000,
            maxreqs=1000,
            maxdeps=1000,
            usemagic=False,
            straightline=False,
            enablephysics=False,
            aligntop=False,
            disableallphysics=False,
            debugperformance=False,
            byrepos=False,
            showallvdeps=False))
        dbinfo = DbInfo()
        start_message("Loading local database ...")
        dbinfo.find_all(args.showallvdeps)
        append_message("done")
        start_message("Finding all dependency circles ... ")
        dbinfo.find_circles()
        append_message("done")
        dbinfo.topology_sort(args.usemagic, args.aligntop, args.byrepos)
        dbinfo.calcSizes()

        start_message("Rendering ... ")

        nodes = []
        links = []

        nodes.append({"id": 0,
                      "label": "level 1 group",
                      "level": 0,
                      "shape": "triangleDown",
                      "isize": 0,
                      "csize": 0,
                      "cssize": 0,
                      "deps": "",
                      "reqs": "",
                      "optdeps": "",
                      "desc": "",
                      "version": "",
                      "group": "group",
                      "groups": "",
                      "provides": "",
                      })

        ids = 1
        for pkg in sorted(dbinfo.all_pkgs.values(), key=lambda x: x.level):
            append_message("%s" % pkg.name)
            pkg.id = ids
            ids += 1
            if pkg.level < args.maxlevel:
                group = "normal"
                if pkg.level == 0:
                    group = "standalone"
                elif type(pkg) is GroupInfo:
                    group = "group"
                elif type(pkg) is VDepInfo:
                    group = "vdep"
                    # if not args.showallvdeps and len(pkg.requiredby) == 0:
                    #     continue
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
                              "groups": ", ".join(pkg.groups),
                              "provides": ", ".join(pkg.provides),
                              "desc": pkg.desc,
                              "version": pkg.version,
                              "repo": pkg.repo,
                              })
        ids = 0
        for pkg in sorted(dbinfo.all_pkgs.values(), key=lambda x: x.level):
            if pkg.level < args.maxlevel:
                if len(pkg.deps) == 0 and len(pkg.requiredby) == 0:
                    links.append({"id": ids,
                                  "from": pkg.id,
                                  "to": 0})
                    ids += 1
                if len(pkg.deps) < args.maxdeps:
                    for dep in pkg.deps:
                        if dep not in pkg.circledeps:
                            if len(dbinfo.get(dep).requiredby) < args.maxreqs:
                                links.append({"id": ids,
                                              "from": pkg.id,
                                              "to": dbinfo.get(dep).id})
                                ids += 1
                for dep in pkg.circledeps:
                    if (pkg.id != dbinfo.get(dep).id):
                        links.append({"id": ids,
                                      "to": pkg.id,
                                      "from": dbinfo.get(dep).id,
                                      "color": "rgb(244,67,54,0.8)"})
                        ids += 1
                for dep in pkg.optdeps:
                    if dep in dbinfo.all_pkgs:
                        links.append({"id": ids,
                                      "from": pkg.id,
                                      "to": dbinfo.get(dep).id,
                                      "dashes": True,
                                      "color": "rgb(255,235,59)"})
                        ids += 1
        print_message("Writing HTML")
        self.render("templates/index.template.html",
                    nodes=json.dumps(nodes),
                    links=json.dumps(links),
                    options=args,
                    optionsjson=json.dumps(args.__dict__))


def make_app():
    import os
    return tornado.web.Application([
        (r"/", MainHandler),
        ], debug=True,
        static_path=os.path.join(os.path.dirname(__file__), "static"))


def main():
    argp = ArgumentParser(description='start PacVis server', formatter_class=ArgumentDefaultsHelpFormatter)
    argp.add_argument('-p', '--port', type=int, default=8888, help='listen at given port')
    argp.add_argument('-s', '--host', type=str, default='localhost', help='listen at given hostname')
    argp.add_argument('-b', '--browser', action='store_true', help='start a browser')
    args = argp.parse_args()
    app = make_app()
    app.listen(args.port, address=args.host)
    print_message(f"Start PacVis at http://{args.host}:{args.port}/")
    if args.browser:
        import os
        cmd = f'xdg-open "http://{args.host}:{args.port}/"'
        print_message(f'running: {cmd}')
        os.system(f'xdg-open "http://{args.host}:{args.port}/"')
    else:
        print_message('use --browser to open a browser automatically.')
    tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
    main()

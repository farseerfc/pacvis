#!/usr/bin/env python3
import pyalpm
import pycman
import tarfile
import sys, os, os.path

pacmanconf = pycman.config.init_with_config("/etc/pacman.conf")
rootdir = pacmanconf.rootdir

def local_database():
	handle = pacmanconf
	localdb = handle.get_localdb()
	packages = localdb.pkgcache
	syncdbs = handle.get_syncdbs()
	db = dict()
	for pkg in packages:
		for syncdb in syncdbs:
			if syncdb.get_pkg(pkg.name) is not None:
				db[pkg.name] = syncdb.get_pkg(pkg.name)
	return db

def get_pkgfiles(package):
	db = local_database()
	pkg = db[package].filename
	result = []
	for d in pacmanconf.cachedirs:
		p = os.path.join(d, pkg)
		if os.path.exists(p):
			result.append(p)
	return result

def error_file(file, pkgfile, pkgname):
	print(f'"{{file}}" in {{pkgfile}} of {{pkgname}} mismatch')

def check_pkgfile(pkgname, pkgfile):
	with tarfile.open(pkgfile) as tar:
		for fn in tar:
			fnpath = os.path.join(rootdir, fn.name)
			if fn.isdir():
				if not os.path.isdir(fnpath):
					error_file(fnpath, pkgfile, pkgname)
			# else if fn.issym():
			# 	if not os.path.issym(fnpath):

def main():
	for pkgname in sys.args:
		for pkgfile in get_pkgfiles(pkgname):
			check_pkgfile(pkgname, pkgfile)

if __name__ == '__main__':
	main()

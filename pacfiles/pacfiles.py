#!/usr/bin/env python3
import pyalpm
import pycman

def local_database():
	handle = pycman.config.init_with_config("/etc/pacman.conf")
	localdb = handle.get_localdb()
	packages = localdb.pkgcache
	syncdbs = handle.get_syncdbs()
	db = dict()
	for pkg in packages:
		for syncdb in syncdbs:
			if syncdb.get_pkg(pkg.name) is not None:
				db[pkg.name] = syncdb.get_pkg(pkg.name)
	return db

def get_files(package):
	db = local_database()
	pkg = db[package]
	files = (x[0] for x in pkg.files)
	return files

def main():
	print(local_database()["pacman"].filename)
	print("\n".join(get_files("pacman")))

if __name__ == '__main__':
	main()
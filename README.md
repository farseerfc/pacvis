# pacvis

Visualize pacman local database using [Vis.js](http://visjs.org/),
inspired by [pacgraph](http://kmkeen.com/pacgraph/).

See a live demo at https://pacvis.farseerfc.me/ showing database of my arch server.

![full](screenshots/full.png)
![zoomin](screenshots/zoomin.png)

## How to use

Install dependencies:
```bash
pacman -S python-tornado pyalpm
```

Then

```python
python pacvis.py
```

Then go to http://localhost:8888/ .

You may need to zoom-in initially to see the rendered picture.
~~Currenly we have scalability issue when there are too may packages, so we need
`maxlevel` to limit the level of dependency depth.~~ We fixed the scalability
issue with a modified vis.js.

## To be improved ...

- [ ] we resolve dependency to package name using pyalpm directly now,
      and this information is lost on the graph
- [ ] we do not track optdepends now
- [ ] we need to estimate removable size (by `pacman -Rcs`)
- [ ] performance for layout algorithm can be improved
- [ ] more information from pacman can be intergrated
- [ ] search by package name
- [ ] show only part of the packages (like `pactree`) instead of filtering by levels
- [ ] be visually attractive!

# pacvis

Visualize pacman local database using [Vis.js](http://visjs.org/),
inspired by [pacgraph](http://kmkeen.com/pacgraph/).

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

Then go to `http://localhost:8888/?maxlevel=30`.

You may need to zoom-in initially to see the rendered picture.
Currenly we have scalability issue when there are too may packages, so we need
`maxlevel` to limit the level of dependency depth.

To be continued ...

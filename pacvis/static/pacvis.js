function filesize(size) {
  var units = "KMGT";
  var left = size;
  var unit = -1;
  for (; left > 1100 && unit < 3; unit++) {
    left /= 1024;
  }
  if (unit === -1) {
    return size + "B";
  } else {
    if (size < 0)
      left = -left;
    return Math.round(left * 100) / 100 + units[unit] + "iB";
  }
}

function size2value(size) { return Math.sqrt(Math.sqrt(size)) / 5; }

function createPkgListDom(list) {
  let depsdom = "";
  if (list == "")
    return "";
  for (let dep of list.split(", ")) {
    depsdom += "<button onclick='document.getElementById(\"search\").value=\"" +
               dep + "\";trysearch()'>" + dep + "</button>";
  }
  return depsdom;
}

function selectPkg(node) {
  document.getElementById("pkgname").innerHTML = node.label;

  document.getElementById("fsinfo").style.display = "block";

  var selectsize = document.getElementById("selectsize");
  document.getElementById("pkgsize").innerHTML =
      selectsize.options[selectsize.selectedIndex].text + ": " +
      filesize(node[selectsize.value]);
  let reason = node.group == "normal" ? "as a dependency" : "explicitly";
  document.getElementById("pkgreason").innerHTML = reason;
  document.getElementById("pkgversion").innerHTML = node.version;
  document.getElementById("pkgdesc").innerHTML = node.desc;
  document.getElementById("pkglevel").innerHTML = node.level;
  document.getElementById("pkgdeps").innerHTML = createPkgListDom(node.deps);
  document.getElementById("pkgreqs").innerHTML = createPkgListDom(node.reqs);
  document.getElementById("pkgoptdeps").innerHTML = createPkgListDom(node.optdeps);
}

function togglehide() {
  let pkgname = document.getElementById("pkgname").innerHTML;
  for (let node of nodes.get()) {
    if (node.label == pkgname) {
      var hide = !node.hidden;
      nodes.update({id : node.id, hidden : hide});
      for (let edge of edges.get()) {
        if (edge.from == node.id) {
          edges.update(
              {id : edge.id, hidden : hide || nodes.get()[edge.to].hidden});
        }
        if (edge.to == node.id) {
          edges.update(
              {id : edge.id, hidden : nodes.get()[edge.from].hidden || hide});
        }
      }
      selectPkg(node);
      network.stabilize(50);
    }
  }
}

function trysearch() {
  let pkgname = document.getElementById("search").value;
  for (let node of nodes.get()) {
    if (node.label == pkgname) {
      network.selectNodes([ node.id ]);
      selectPkg(node);
      if (!node.hidden) {
        network.focus(node.id, {
          scale : Math.log(nodes.length) / 5,
          locked : false,
          animation : {duration : 500, easingFunction : "linear"}
        });
      }
    }
  }
}

function switchsize() {
  let selectsize = document.getElementById("selectsize");
  let size = selectsize.options[selectsize.selectedIndex].value;
  let pkgname = document.getElementById("pkgname").innerHTML;
  for (let node of nodes.get()) {
    nodes.update({id : node.id, value : size2value(node[size])});
    if (node.label == pkgname) {
      selectPkg(node);
    }
  }
}

function close_panel() {
  document.querySelector('#leftpanel').style.display = "none";
  document.querySelector('#leftpanel_show').style.display = "block";
}

function show_panel() {
  document.querySelector('#leftpanel').style.display = "block";
  document.querySelector('#leftpanel_show').style.display = "none";
}

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
    return "<i>Nothing</i>";
  for (let dep of list.split(", ")) {
    depsdom += "<button class=\"mdl-button mdl-js-button mdl-js-ripple-effect\" onclick='document.getElementById(\"search\").value=\"" +
               dep + "\";trysearch()'>" + dep + "</a> ";
  }
  return depsdom;
}

var deselectTimeout = null;

function selectPkg(node) {
  clearTimeout(deselectTimeout);
  document.getElementById("fsinfo").style.display = "block";
  document.querySelector('#fsinfo').className = "mdl-card mdl-shadow--4dp animated zoomIn";
  document.getElementById("pkgname").innerHTML = node.label;
  document.getElementById("pkgsizedesc").innerHTML = document.querySelector('#currentsizedesc').innerHTML;
  document.getElementById("pkgsize").innerHTML =  filesize(node[currentsize]);
  let reason = node.group == "normal" ? "as a dependency" : "explicitly";
  document.getElementById("pkgreason").innerHTML = reason;
  document.getElementById("pkgversion").innerHTML = node.version;
  document.getElementById("pkgdesc").innerHTML = node.desc;
  document.getElementById("pkglevel").innerHTML = node.level;
  document.getElementById("pkgdeps").innerHTML = createPkgListDom(node.deps);
  document.getElementById("badgedep").setAttribute('data-badge', node.deps=="" ? 0 : node.deps.split(', ').length);
  document.getElementById("pkgreqs").innerHTML = createPkgListDom(node.reqs);
  document.getElementById("badgereq").setAttribute('data-badge', node.reqs=="" ? 0 : node.reqs.split(', ').length);
  document.getElementById("pkgoptdeps").innerHTML = createPkgListDom(node.optdeps);
  document.getElementById("badgeoptdep").setAttribute('data-badge', node.optdeps=="" ? 0 : node.optdeps.split(', ').length);
}

function deselectPkg(){
  document.querySelector('#fsinfo').className = "mdl-card mdl-shadow--4dp animated zoomOut";
  deselectTimeout = setTimeout(function(){
    document.getElementById("fsinfo").style.display = "none";
  }, 300);

  // hide search content
  document.getElementById("search").value = "";
  document.getElementById("searchwrapper").className =
    document.getElementById("searchwrapper").className.replace(/\bis-dirty\b/,'');
  document.getElementById("searchwrapper").className =
    document.getElementById("searchwrapper").className.replace(/\bis-focused\b/,'');
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
          animation : {duration : 300}
        });
      }
    }
  }
}


function switchsizeto(size){
  let pkgname = document.getElementById("pkgname").innerHTML;
  for (let node of nodes.get()) {
    nodes.update({id : node.id, value : size2value(node[size])});
    if (node.label == pkgname) {
      selectPkg(node);
    }
  }
}

function close_panel() {
  document.querySelector('#lefttoppanel').className = "lefttoppanel animated zoomOut";
  document.querySelector('#leftpanel_show').style.display = "block";
  document.querySelector('#leftpanel_show').className = "leftpanel-show mdl-button mdl-js-button mdl-button--fab mdl-js-ripple-effect animated zoomIn";
  setTimeout(function(){
    document.querySelector('#lefttoppanel').style.display = "none";
  }, 300);
}

function show_panel() {
  document.querySelector('#lefttoppanel').style.display = "flex";
  document.querySelector('#lefttoppanel').className = "lefttoppanel animated zoomIn";
  document.querySelector('#leftpanel_show').className = "leftpanel-show mdl-button mdl-js-button mdl-button--fab mdl-js-ripple-effect animated zoomOut";
}

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

function size2value(size) { return size==0 ? 12 : Math.sqrt(Math.sqrt(size)) / 5; }

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

var highlightActive = false;

function neighbourhoodHighlight(params) {
    var nodesDataset = nodes;
    var edgesDataset = edges;
    var allNodes = nodedata;
    // if something is selected:
    if (params.nodes.length > 0) {
      highlightActive = true;
      var i,j;
      var selectedNode = params.nodes[0];
      var degrees = 2;

      // mark all nodes as hard to read.
      for (var nodeId in allNodes) {
        allNodes[nodeId].color = 'rgba(200,200,200,0.5)';
        if (allNodes[nodeId].hiddenLabel === undefined) {
          allNodes[nodeId].hiddenLabel = allNodes[nodeId].label;
          allNodes[nodeId].label = undefined;
        }
      }
      var connectedNodes = network.getConnectedNodes(selectedNode);
      var allConnectedNodes = [];

      // get the second degree nodes
      for (i = 1; i < degrees; i++) {
        for (j = 0; j < connectedNodes.length; j++) {
          allConnectedNodes = allConnectedNodes.concat(network.getConnectedNodes(connectedNodes[j]));
        }
      }

      // all second degree nodes get a different color and their label back
      for (i = 0; i < allConnectedNodes.length; i++) {
        allNodes[allConnectedNodes[i]].color = 'rgba(150,150,150,0.75)';
        if (allNodes[allConnectedNodes[i]].hiddenLabel !== undefined) {
          allNodes[allConnectedNodes[i]].label = allNodes[allConnectedNodes[i]].hiddenLabel;
          allNodes[allConnectedNodes[i]].hiddenLabel = undefined;
        }
      }

      // all first degree nodes get their own color and their label back
      for (i = 0; i < connectedNodes.length; i++) {
        allNodes[connectedNodes[i]].color = undefined;
        if (allNodes[connectedNodes[i]].hiddenLabel !== undefined) {
          allNodes[connectedNodes[i]].label = allNodes[connectedNodes[i]].hiddenLabel;
          allNodes[connectedNodes[i]].hiddenLabel = undefined;
        }
      }

      // the main node gets its own color and its label back.
      allNodes[selectedNode].color = undefined;
      if (allNodes[selectedNode].hiddenLabel !== undefined) {
        allNodes[selectedNode].label = allNodes[selectedNode].hiddenLabel;
        allNodes[selectedNode].hiddenLabel = undefined;
      }
    }
    else if (highlightActive === true) {
      // reset all nodes
      for (var nodeId in allNodes) {
        allNodes[nodeId].color = undefined;
        if (allNodes[nodeId].hiddenLabel !== undefined) {
          allNodes[nodeId].label = allNodes[nodeId].hiddenLabel;
          allNodes[nodeId].hiddenLabel = undefined;
        }
      }
      highlightActive = false
    }

    // transform the object into an array
    var updateArray = [];
    for (nodeId in allNodes) {
      if (allNodes.hasOwnProperty(nodeId)) {
        updateArray.push(allNodes[nodeId]);
      }
    }
    nodesDataset.update(updateArray);

  }

var deselectTimeout = null;

function showPkgInfo(node) {
  clearTimeout(deselectTimeout);
  document.getElementById("fsinfo").style.display = "block";
  document.querySelector('#fsinfo').className = "mdl-card mdl-shadow--4dp animated zoomIn";
  let label = node.label || node.hiddenLabel
  document.getElementById("pkgname").innerHTML = label;
  document.getElementById("pkgsizedesc").innerHTML = {"isize":"Installed", "csize":"Cascade", "cssize":"Recursive"}[currentsize] + " Size";
  document.getElementById("pkgsize").innerHTML =  filesize(node[currentsize]);
  let reason = node.group == "normal" ? "as a dependency" : "explicitly";
  document.getElementById("pkgreason").innerHTML = reason;
  document.getElementById("pkgversion").innerHTML = node.version;
  document.getElementById("pkgdesc").innerHTML = node.desc;
  document.getElementById("pkglevel").innerHTML = node.level;
  document.getElementById("pkgrepo").innerHTML = node.repo;
  document.getElementById("pkgdeps").innerHTML = createPkgListDom(node.deps);
  document.getElementById("badgedep").setAttribute('data-badge', node.deps=="" ? 0 : node.deps.split(', ').length);
  document.getElementById("pkgreqs").innerHTML = createPkgListDom(node.reqs);
  document.getElementById("badgereq").setAttribute('data-badge', node.reqs=="" ? 0 : node.reqs.split(', ').length);
  document.getElementById("pkgoptdeps").innerHTML = createPkgListDom(node.optdeps);
  document.getElementById("badgeoptdep").setAttribute('data-badge', node.optdeps=="" ? 0 : node.optdeps.split(', ').length);
  document.getElementById("pkggroups").innerHTML = createPkgListDom(node.groups);
  document.getElementById("pkgprovides").innerHTML = node.provides;
}

function selectPkg(node) {
  let label = node.label || node.hiddenLabel
  document.getElementById("search").value = label;
  document.getElementById("search-list").style.display = 'none';
  network.selectNodes([node.id]);
  showPkgInfo(node)
  network.focus(node.id, {
    scale: Math.log(nodes.length) / 5,
    locked: false,
    animation: { duration: 300 }
  });
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
  document.getElementById("search-list").style.display = 'none';
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

// from https://github.com/aceakash/string-similarity
// Copyright (c) 2018 Akash Kurdekar, licensed under MIT
function compareTwoStrings(first, second) {
	first = first.replace(/\s+/g, '')
	second = second.replace(/\s+/g, '')

	if (first === second) return 1; // identical or empty
	if (first.length < 2 || second.length < 2) return 0; // if either is a 0-letter or 1-letter string

	let firstBigrams = new Map();
	for (let i = 0; i < first.length - 1; i++) {
		const bigram = first.substring(i, i + 2);
		const count = firstBigrams.has(bigram)
			? firstBigrams.get(bigram) + 1
			: 1;

		firstBigrams.set(bigram, count);
	};

	let intersectionSize = 0;
	for (let i = 0; i < second.length - 1; i++) {
		const bigram = second.substring(i, i + 2);
		const count = firstBigrams.has(bigram)
			? firstBigrams.get(bigram)
			: 0;

		if (count > 0) {
			firstBigrams.set(bigram, count - 1);
			intersectionSize++;
		}
	}

	return (2.0 * intersectionSize) / (first.length + second.length - 2);
}

// return a list of similar match, sorted by similarity
function findmatch(pattern) {
  return (
    nodes.get()
      .sort() // sort alphabetically first
      .sort((a, b) => {
        let aLabel = a.label || a.hiddenLabel
        let bLabel = b.label || b.hiddenLabel
        return (
          compareTwoStrings(pattern, bLabel) - compareTwoStrings(pattern, aLabel)
        )
      })
      .slice(0, 5)
  );
}

function trysearch() {
  let pkgname = document.getElementById("search").value;
  let found = findmatch(pkgname);
  let searchList = document.getElementById("search-list");
  searchList.innerHTML = found.map(node => {
    let label = node.label || node.hiddenLabel
    let highlighted = label.replace(pkgname, `<b>${pkgname}</b>`);
    return (
      `<li class="mdl-list__item" data-nodeid="${node.id}">${highlighted}</li>`
    );
  }).join('')
  searchList.style.display = pkgname ? "block" : "none";
  for (let el of searchList.children) {
    el.addEventListener('click', searchItemClick);
  }
}

function searchItemClick(event) {
  let node = nodes.get(event.target.dataset.nodeid);
  selectPkg(node)
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

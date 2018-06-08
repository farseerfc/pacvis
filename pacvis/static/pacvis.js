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

function selectPkg(node) {
  clearTimeout(deselectTimeout);
  document.getElementById("fsinfo").style.display = "block";
  document.querySelector('#fsinfo').className = "mdl-card mdl-shadow--4dp animated zoomIn";
  document.getElementById("pkgname").innerHTML = node.label;
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

function pacvisDom() {
  function ifNeedReload(){
    let need = false;
    for(key in pacvisopts){
      let v = pacvisopts[key];
      let dom = document.querySelector("#"+key);
      if(dom){
        let cv = Number.isInteger(v) ? dom.value : dom.checked;
        need = need || cv != v;
      }
      need = need || !document.querySelector("#option-"+currentsize).checked;
    }
    if(need){
      document.querySelector('#reloadbtn').className = "mdl-button mdl-js-button mdl-button--raised mdl-button--colored";
    }else{
      document.querySelector('#reloadbtn').className = "mdl-button mdl-js-button mdl-button--primary";
    }
  }
  for(key in pacvisopts){
    let dom = document.querySelector("#"+key);
    if(dom) {
      if(Number.isInteger(pacvisopts[key])){
        dom.addEventListener("input", ifNeedReload);
      }else{
        dom.addEventListener("change" , ifNeedReload);
      }
    }
  }
  document.querySelector("#option-isize").addEventListener("change" , ifNeedReload);
  document.querySelector("#option-csize").addEventListener("change" , ifNeedReload);
  document.querySelector("#option-cssize").addEventListener("change" , ifNeedReload);

  document.querySelector('#search').addEventListener('input', trysearch);
  document.querySelector('#close_button').addEventListener('click', close_panel);
  document.querySelector('#leftpanel_show').addEventListener('click', show_panel);
  document.querySelector('#advanced_menu').addEventListener('click', function(){
    if (document.querySelector('#advanced_form').style.display == "block"){
      document.querySelector('#advanced_form').style.display = "none";
    }else{
      document.querySelector('#advanced_form').style.display = "block";
      document.querySelector('#legend_panel').style.display = "none";
    }
  });
  document.querySelector('#legend-btn').addEventListener('click', function(){
    if (document.querySelector('#legend_panel').style.display == "block"){
      document.querySelector('#legend_panel').style.display = "none";
    }else{
      document.querySelector('#legend_panel').style.display = "block";
      document.querySelector('#advanced_form').style.display = "none";
      let legend_options = JSON.parse(JSON.stringify(options)); // deep copy
      legend_options.layout = {
         hierarchical: {
             direction: "UD",
             nodeSpacing: 50,
             treeSpacing: 50,
             levelSeparation: 100,
             blockShifting: false,
             edgeMinimization: false,
             parentCentralization: false
         },
        improvedLayout: true
      };
      legend_options.physics = false;
      let legend = new vis.Network(document.querySelector("#legend_target"), {
        nodes: [
          {
            id: "normal-legend",
            label: "packages installed as dependencies",
            level: 0,
            group: "normal",
            value: size2value(0),
          },
          {
            id: "explicit-legend",
            label: "packages installed explicitly",
            level: 2,
            group: "explicit",
            value: size2value(0),
          },
          {
            id: "group-legend",
            label: "package groups",
            level: 4,
            group: "group",
            value: size2value(0),
          },
          {
            id: "vdep-legend",
            label: "virtual dependencies (in provides)",
            level: 6,
            group: "vdep",
            value: size2value(0),
          },
        ],
        edges: [
          { from: "normal-legend", to: "explicit-legend" },
          { from: "explicit-legend", to: "group-legend" },
          { from: "group-legend", to: "vdep-legend" },
        ]
      }, legend_options);

      legend.fit();
      setTimeout(function(){
        legend.moveTo({scale: legend.getScale()*0.85, animation : {duration : 300}});
      }, 50);
    }
  });
  document.querySelector('#enablephysics').addEventListener('change', function(){
    if(this.checked){
      network.setOptions({physics: physics});
    }else{
      network.setOptions({physics: false});
    }
  });
  document.querySelector('#loading_progress').addEventListener('mdl-componentupgraded', pacvis);

  document.querySelector('#zoomin').addEventListener('click', function(){
    network.moveTo({'scale': network.getScale()*2, animation : {duration : 300}});
  });

  document.querySelector('#zoomout').addEventListener('click', function(){
    network.moveTo({'scale': network.getScale()*0.5, animation : {duration : 300}});
  });

  document.querySelector('#zoomfit').addEventListener('click', function(){
    network.fit({animation : {duration : 300}});
  });
}

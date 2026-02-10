/* DeepTrace Dashboard — app.js */

var graphNetwork = null;
var graphData = null;

function initGraph() {
  var container = document.getElementById('network-graph');
  if (!container || typeof vis === 'undefined') return;

  fetch('/network/graph')
    .then(function(r) { return r.json(); })
    .then(function(data) {
      graphData = data;
      renderGraph(data);
    });
}

function renderGraph(data) {
  var container = document.getElementById('network-graph');
  if (!container) return;

  var nodes = new vis.DataSet(data.nodes);
  var edges = new vis.DataSet(data.edges);

  var options = {
    physics: {
      barnesHut: {
        gravitationalConstant: -20000,
        centralGravity: 0.5,
        springLength: 120,
        springConstant: 0.06,
        damping: 0.12
      },
      minVelocity: 0.75,
      maxVelocity: 40
    },
    interaction: {
      hover: true,
      tooltipDelay: 80,
      navigationButtons: false,
      zoomView: true
    },
    nodes: {
      font: {
        color: '#c8cad0',
        size: 11,
        face: "'JetBrains Mono', 'SF Mono', monospace",
        strokeWidth: 3,
        strokeColor: '#06070b'
      },
      borderWidth: 1,
      borderWidthSelected: 2,
      shadow: {
        enabled: true,
        color: 'rgba(0,0,0,0.4)',
        size: 8,
        x: 0,
        y: 2
      }
    },
    edges: {
      font: {
        color: '#6b7084',
        size: 9,
        strokeWidth: 0,
        face: "'JetBrains Mono', 'SF Mono', monospace"
      },
      smooth: { type: 'continuous', roundness: 0.3 },
      width: 1,
      color: { opacity: 0.5, inherit: false },
      hoverWidth: 0.5,
      selectionWidth: 1
    }
  };

  graphNetwork = new vis.Network(container, { nodes: nodes, edges: edges }, options);

  graphNetwork.on('click', function(params) {
    if (params.nodes.length > 0) {
      var nodeId = params.nodes[0];
      var parts = nodeId.split(':');
      if (parts.length === 2) {
        var type = parts[0];
        var id = parts[1];
        var routeMap = {
          'entity': null,
          'evidence': '/evidence/' + id,
          'event': '/timeline/' + id,
          'hypothesis': '/hypotheses/' + id,
          'suspect': '/suspects/' + id,
          'source': '/sources/' + id,
          'attachment': '/files/' + id
        };
        var route = routeMap[type];
        if (route) {
          htmx.ajax('GET', route, {target: '#detail-panel', swap: 'innerHTML'});
        }
      }
    }
  });

  graphNetwork.once('stabilizationIterationsDone', function() {
    graphNetwork.fit({ animation: { duration: 500, easingFunction: 'easeInOutQuad' } });
  });
}

function resetGraph() {
  if (graphNetwork) {
    graphNetwork.fit({ animation: { duration: 400, easingFunction: 'easeInOutQuad' } });
  }
}

function togglePhysics() {
  if (graphNetwork) {
    var physics = graphNetwork.physics.options.enabled;
    graphNetwork.setOptions({ physics: { enabled: !physics } });
  }
}

function applyFilters() {
  if (!graphData) return;

  var groups = ['entity', 'evidence', 'event', 'hypothesis', 'suspect_pool', 'source', 'attachment'];
  var visible = {};
  groups.forEach(function(g) {
    var cb = document.getElementById('filter-' + g);
    visible[g] = cb ? cb.checked : true;
  });

  var filteredNodes = graphData.nodes.filter(function(n) { return visible[n.group]; });
  var nodeIds = {};
  filteredNodes.forEach(function(n) { nodeIds[n.id] = true; });
  var filteredEdges = graphData.edges.filter(function(e) { return nodeIds[e.from] && nodeIds[e.to]; });

  renderGraph({ nodes: filteredNodes, edges: filteredEdges });
}

/* HTMX: after content swap, re-init graph if needed */
document.body.addEventListener('htmx:afterSwap', function(evt) {
  var graphEl = document.getElementById('network-graph');
  if (graphEl) {
    if (typeof vis !== 'undefined') {
      setTimeout(initGraph, 50);
    } else {
      var script = document.createElement('script');
      script.src = '/static/vis-network.min.js';
      script.onload = function() { setTimeout(initGraph, 50); };
      document.head.appendChild(script);
    }
  }
});

/* Update active nav item on HTMX navigation */
document.body.addEventListener('htmx:afterSwap', function(evt) {
  if (evt.detail.target && evt.detail.target.id === 'main-content') {
    var url = window.location.pathname;
    document.querySelectorAll('.nav-item').forEach(function(el) {
      el.classList.remove('active');
      var href = el.getAttribute('href');
      if (href === url || (href !== '/' && url.startsWith(href))) {
        el.classList.add('active');
      } else if (href === '/' && url === '/') {
        el.classList.add('active');
      }
    });
  }
});

/* === File Upload: Drag & Drop === */
document.body.addEventListener('htmx:afterSwap', function() {
  var dropZone = document.getElementById('drop-zone');
  var fileInput = document.getElementById('file-input');
  if (!dropZone || !fileInput) return;

  dropZone.addEventListener('click', function() { fileInput.click(); });
  dropZone.addEventListener('keydown', function(e) {
    if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); fileInput.click(); }
  });

  fileInput.addEventListener('change', function() {
    if (fileInput.files.length > 0) {
      document.getElementById('file-selected-name').textContent =
        fileInput.files[0].name + ' (' + (fileInput.files[0].size / 1024).toFixed(1) + ' KB)';
      document.getElementById('file-preview-info').style.display = 'block';
    }
  });

  ['dragenter', 'dragover'].forEach(function(ev) {
    dropZone.addEventListener(ev, function(e) {
      e.preventDefault(); e.stopPropagation(); dropZone.classList.add('drag-over');
    });
  });
  ['dragleave', 'drop'].forEach(function(ev) {
    dropZone.addEventListener(ev, function(e) {
      e.preventDefault(); e.stopPropagation(); dropZone.classList.remove('drag-over');
    });
  });
  dropZone.addEventListener('drop', function(e) {
    if (e.dataTransfer.files.length > 0) {
      fileInput.files = e.dataTransfer.files;
      fileInput.dispatchEvent(new Event('change', { bubbles: true }));
    }
  });
});

/* === Image Lightbox (accessible) === */
function openLightbox(src) {
  var previousFocus = document.activeElement;
  var overlay = document.createElement('div');
  overlay.className = 'lightbox-overlay';
  overlay.setAttribute('role', 'dialog');
  overlay.setAttribute('aria-modal', 'true');
  overlay.setAttribute('aria-label', 'Image preview');

  var closeBtn = document.createElement('button');
  closeBtn.className = 'lightbox-close';
  closeBtn.setAttribute('aria-label', 'Close image preview');
  closeBtn.textContent = '\u00D7';
  closeBtn.style.cssText = 'position:absolute;top:1rem;right:1rem;background:rgba(0,0,0,0.7);color:#fff;border:none;font-size:2rem;width:3rem;height:3rem;border-radius:50%;cursor:pointer;z-index:10001;display:flex;align-items:center;justify-content:center;';

  var img = document.createElement('img');
  img.src = src;
  img.alt = 'Full size preview';
  img.onclick = function(e) { e.stopPropagation(); };

  function closeLightbox() {
    if (document.body.contains(overlay)) {
      document.body.removeChild(overlay);
      document.removeEventListener('keydown', handleKeys);
      if (previousFocus) previousFocus.focus();
    }
  }

  function handleKeys(e) {
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'Tab') {
      e.preventDefault();
      closeBtn.focus();
    }
  }

  overlay.onclick = closeLightbox;
  closeBtn.onclick = function(e) { e.stopPropagation(); closeLightbox(); };

  overlay.appendChild(closeBtn);
  overlay.appendChild(img);
  document.body.appendChild(overlay);
  document.addEventListener('keydown', handleKeys);
  closeBtn.focus();
}

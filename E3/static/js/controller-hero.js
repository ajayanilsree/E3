import * as THREE from "./vendor/three.module.min.js";

(function () {
  var mount = document.querySelector("[data-controller-hero]");
  if (!mount || !THREE.WebGLRenderer) return;

  var loginUrl = mount.getAttribute("data-login-url") || "/accounts/login/";
  var joinUrl = mount.getAttribute("data-join-url") || "/register/";
  var touchpadLogoUrl = mount.getAttribute("data-touchpad-logo-url") || "";

  var prefersReducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var scene = new THREE.Scene();
  scene.background = new THREE.Color(0x000000);

  var camera = new THREE.PerspectiveCamera(32, 1, 0.1, 100);
  camera.position.set(0, 0.18, 10.5);

  var renderer = new THREE.WebGLRenderer({
    antialias: true,
    alpha: false,
    powerPreference: "high-performance"
  });
  renderer.setClearColor(0x000000, 1);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 2));
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.2;
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  mount.appendChild(renderer.domElement);

  var controller = new THREE.Group();
  controller.rotation.x = -0.18;
  scene.add(controller);

  var raycaster = new THREE.Raycaster();
  var textureLoader = new THREE.TextureLoader();
  var pointer = new THREE.Vector2(999, 999);
  var interactiveTargets = [];
  var decorativeTargets = [];
  var activeStick = null;
  var hoveredStick = null;
  var activeDecorative = null;
  var hoveredDecorative = null;
  var launchTimer = 0;
  var oledTimer = 0;
  var oledState = {
    active: false,
    fading: false,
    startedAt: 0,
    fadeStartedAt: 0,
    action: null,
    opacity: 0
  };
  var BRAND = {
    black: 0x000000,
    charcoal: 0x222222,
    lowerBlack: 0x000000,
    gunmetal: 0x1b1b1b,
    darkGrey: 0x3a3a3a,
    white: 0xffffff,
    ash: 0xd1cec9,
    red: 0xd9080a,
    legendRed: 0xc1121f
  };

  function createMicroGrainTexture() {
    var canvas = document.createElement("canvas");
    canvas.width = 128;
    canvas.height = 128;
    var ctx = canvas.getContext("2d");
    ctx.fillStyle = "rgb(128,128,128)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);
    for (var y = 0; y < canvas.height; y += 1) {
      for (var x = 0; x < canvas.width; x += 1) {
        var grain = 110 + Math.random() * 34;
        ctx.fillStyle = "rgb(" + grain + "," + grain + "," + grain + ")";
        ctx.fillRect(x, y, 1, 1);
      }
    }
    var texture = new THREE.CanvasTexture(canvas);
    texture.wrapS = THREE.RepeatWrapping;
    texture.wrapT = THREE.RepeatWrapping;
    texture.repeat.set(24, 14);
    texture.needsUpdate = true;
    return texture;
  }

  var shellGrainTexture = createMicroGrainTexture();

  var whitePlastic = new THREE.MeshPhysicalMaterial({
    color: BRAND.charcoal,
    roughness: 0.72,
    metalness: 0.03,
    clearcoat: 0.34,
    clearcoatRoughness: 0.48,
    reflectivity: 0.38,
    bumpMap: shellGrainTexture,
    bumpScale: 0.026
  });
  var sidePlastic = new THREE.MeshPhysicalMaterial({
    color: BRAND.lowerBlack,
    roughness: 0.56,
    metalness: 0.02,
    clearcoat: 0.26,
    clearcoatRoughness: 0.42,
    bumpMap: shellGrainTexture,
    bumpScale: 0.015
  });
  var blackRubber = new THREE.MeshPhysicalMaterial({
    color: BRAND.black,
    roughness: 0.74,
    metalness: 0,
    clearcoat: 0.08,
    clearcoatRoughness: 0.68
  });
  var glossyBlack = new THREE.MeshPhysicalMaterial({
    color: BRAND.black,
    roughness: 0.12,
    metalness: 0.01,
    clearcoat: 1,
    clearcoatRoughness: 0.08,
    reflectivity: 0.72
  });
  var labelMaterial = new THREE.MeshPhysicalMaterial({
    color: BRAND.charcoal,
    roughness: 0.42,
    metalness: 0,
    clearcoat: 0.85,
    clearcoatRoughness: 0.18
  });
  var seamMaterial = new THREE.LineBasicMaterial({
    color: BRAND.ash,
    transparent: true,
    opacity: 0.24
  });
  var redAccentMaterial = new THREE.MeshBasicMaterial({
    color: BRAND.red,
    transparent: true,
    opacity: 0.18,
    depthWrite: false
  });
  var whiteAccentMaterial = new THREE.MeshBasicMaterial({
    color: BRAND.white,
    transparent: true,
    opacity: 0.14,
    depthWrite: false
  });
  var gunmetalMaterial = new THREE.MeshPhysicalMaterial({
    color: BRAND.gunmetal,
    roughness: 0.28,
    metalness: 0.38,
    clearcoat: 0.38,
    clearcoatRoughness: 0.18
  });
  var faceButtonMaterial = new THREE.MeshPhysicalMaterial({
    color: BRAND.black,
    roughness: 0.64,
    metalness: 0.02,
    clearcoat: 0.12,
    clearcoatRoughness: 0.58
  });
  var dpadMaterial = new THREE.MeshPhysicalMaterial({
    color: BRAND.black,
    roughness: 0.82,
    metalness: 0,
    clearcoat: 0.12,
    clearcoatRoughness: 0.66,
    bumpMap: shellGrainTexture,
    bumpScale: 0.006
  });

  function createStickLabelTexture(text) {
    var canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 256;
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "800 118px Poppins, Arial, sans-serif";

    ctx.fillStyle = "rgba(0,0,0,.52)";
    ctx.fillText(text, 259, 138);

    ctx.fillStyle = "rgba(245,245,245,.96)";
    ctx.fillText(text, 256, 132);

    ctx.fillStyle = "rgba(255,255,255,.10)";
    ctx.fillText(text, 255, 129);

    var texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }

  function createEngravedTextTexture(text, width, height, fontSize, letterSpacing, color) {
    var canvas = document.createElement("canvas");
    canvas.width = width;
    canvas.height = height;
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, width, height);
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.font = "700 " + fontSize + "px Space Grotesk, Arial, sans-serif";
    ctx.fillStyle = "rgba(0,0,0,.48)";
    ctx.fillText(text, width / 2 + 1, height / 2 + 1);
    ctx.fillStyle = color || "rgba(209,206,201,.22)";
    if (letterSpacing && text.length > 1) {
      var start = width / 2 - ((text.length - 1) * letterSpacing) / 2;
      for (var i = 0; i < text.length; i += 1) {
        ctx.fillText(text[i], start + i * letterSpacing, height / 2);
      }
    } else {
      ctx.fillText(text, width / 2, height / 2);
    }
    var texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }

  function createFaceSymbolTexture(text) {
    var canvas = document.createElement("canvas");
    canvas.width = 220;
    canvas.height = 220;
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    function drawSymbol(offsetX, offsetY, strokeStyle, lineWidth, shadowBlur) {
      ctx.save();
      ctx.translate(offsetX, offsetY);
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.shadowColor = strokeStyle;
      ctx.shadowBlur = shadowBlur || 0;
      ctx.beginPath();

      if (text === "\u25cb") {
        ctx.arc(110, 110, 52, 0, Math.PI * 2);
      } else if (text === "\u25b3") {
        ctx.moveTo(110, 50);
        ctx.lineTo(58, 148);
        ctx.lineTo(162, 148);
        ctx.closePath();
      } else if (text === "\u25a1") {
        ctx.rect(64, 64, 92, 92);
      } else {
        ctx.moveTo(62, 62);
        ctx.lineTo(158, 158);
        ctx.moveTo(158, 62);
        ctx.lineTo(62, 158);
      }

      ctx.stroke();
      ctx.restore();
    }

    // Layered vector strokes keep the legends sharp while suggesting recessed engraving.
    drawSymbol(5, 6, "rgba(0,0,0,.86)", 24, 4);
    drawSymbol(-3, -4, "rgba(255,255,255,.24)", 10, 0);
    drawSymbol(0, 0, "rgba(193,18,31,1)", 18, 1.5);
    drawSymbol(1, 1, "rgba(123,8,14,.42)", 8, 0);

    var texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }

  function createDpadArrowTexture(text) {
    var canvas = document.createElement("canvas");
    canvas.width = 240;
    canvas.height = 240;
    var ctx = canvas.getContext("2d");
    ctx.clearRect(0, 0, canvas.width, canvas.height);

    function drawArrow(offsetX, offsetY, strokeStyle, lineWidth, shadowBlur) {
      ctx.save();
      ctx.translate(offsetX, offsetY);
      ctx.strokeStyle = strokeStyle;
      ctx.lineWidth = lineWidth;
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.shadowColor = strokeStyle;
      ctx.shadowBlur = shadowBlur || 0;
      ctx.beginPath();

      if (text === "\u2191") {
        ctx.moveTo(120, 166);
        ctx.lineTo(120, 74);
        ctx.moveTo(78, 120);
        ctx.lineTo(120, 74);
        ctx.lineTo(162, 120);
      } else if (text === "\u2193") {
        ctx.moveTo(120, 74);
        ctx.lineTo(120, 166);
        ctx.moveTo(78, 120);
        ctx.lineTo(120, 166);
        ctx.lineTo(162, 120);
      } else if (text === "\u2190") {
        ctx.moveTo(166, 120);
        ctx.lineTo(74, 120);
        ctx.moveTo(120, 78);
        ctx.lineTo(74, 120);
        ctx.lineTo(120, 162);
      } else {
        ctx.moveTo(74, 120);
        ctx.lineTo(166, 120);
        ctx.moveTo(120, 78);
        ctx.lineTo(166, 120);
        ctx.lineTo(120, 162);
      }

      ctx.stroke();
      ctx.restore();
    }

    drawArrow(5, 6, "rgba(0,0,0,.86)", 28, 4);
    drawArrow(-3, -4, "rgba(255,255,255,.24)", 11, 0);
    drawArrow(0, 0, "rgba(193,18,31,.62)", 21, 0.4);
    drawArrow(1, 1, "rgba(112,6,13,.34)", 8, 0);

    var texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    texture.needsUpdate = true;
    return texture;
  }

  function createOledTexture() {
    var canvas = document.createElement("canvas");
    canvas.width = 1024;
    canvas.height = 512;
    var texture = new THREE.CanvasTexture(canvas);
    texture.colorSpace = THREE.SRGBColorSpace;
    return {
      canvas: canvas,
      ctx: canvas.getContext("2d"),
      texture: texture
    };
  }

  function roundedCanvasRect(ctx, x, y, width, height, radius) {
    var r = Math.min(radius, width / 2, height / 2);
    ctx.beginPath();
    ctx.moveTo(x + r, y);
    ctx.lineTo(x + width - r, y);
    ctx.quadraticCurveTo(x + width, y, x + width, y + r);
    ctx.lineTo(x + width, y + height - r);
    ctx.quadraticCurveTo(x + width, y + height, x + width - r, y + height);
    ctx.lineTo(x + r, y + height);
    ctx.quadraticCurveTo(x, y + height, x, y + height - r);
    ctx.lineTo(x, y + r);
    ctx.quadraticCurveTo(x, y, x + r, y);
  }

  function drawOledDisplay(oled, action, progress, pulse) {
    var ctx = oled.ctx;
    var width = oled.canvas.width;
    var height = oled.canvas.height;
    var color = action.color;
    var boot = Math.min(progress / 0.32, 1);
    var lineSweep = (progress * 1.65) % 1;
    var pad = 10;
    var displayWidth = width - pad * 2;
    var displayHeight = height - pad * 2;

    ctx.clearRect(0, 0, width, height);
    ctx.save();
    roundedCanvasRect(ctx, pad, pad, displayWidth, displayHeight, 82);
    ctx.clip();

    ctx.globalAlpha = 0.98;
    ctx.fillStyle = "rgba(0, 0, 0, 0.88)";
    ctx.fillRect(pad, pad, displayWidth, displayHeight);

    var glow = ctx.createRadialGradient(width / 2, height / 2, 16, width / 2, height / 2, 520);
    glow.addColorStop(0, color.fill);
    glow.addColorStop(0.58, "rgba(255, 255, 255, 0.035)");
    glow.addColorStop(1, "rgba(0, 0, 0, 0)");
    ctx.globalAlpha = 0.68 + 0.16 * pulse;
    ctx.fillStyle = glow;
    ctx.fillRect(pad, pad, displayWidth, displayHeight);

    ctx.globalAlpha = 0.36 + 0.1 * pulse;
    ctx.strokeStyle = color.stroke;
    ctx.lineWidth = 10;
    ctx.shadowColor = color.stroke;
    ctx.shadowBlur = 30 + 8 * pulse;
    roundedCanvasRect(ctx, pad + 8, pad + 8, displayWidth - 16, displayHeight - 16, 72);
    ctx.stroke();
    ctx.shadowBlur = 0;

    ctx.globalAlpha = 0.08;
    ctx.fillStyle = "#ffffff";
    for (var y = pad + 18; y < height - pad - 18; y += 18) {
      ctx.fillRect(pad + 22, y, displayWidth - 44, 2);
    }

    ctx.globalAlpha = 0.18 * boot;
    ctx.fillStyle = "rgba(217, 8, 10, 0.86)";
    ctx.fillRect(pad + 22, pad + 14 + (displayHeight - 28) * lineSweep, displayWidth - 44, 10);

    ctx.globalAlpha = 0.16 * boot;
    ctx.strokeStyle = "rgba(217, 8, 10, 0.52)";
    ctx.lineWidth = 2;
    ctx.strokeRect(pad + 34, pad + 34, displayWidth - 68, displayHeight - 68);

    ctx.globalAlpha = boot;
    ctx.textAlign = "center";
    ctx.textBaseline = "middle";
    ctx.shadowColor = color.stroke;
    ctx.shadowBlur = 18 + 6 * pulse;

    ctx.strokeStyle = color.stroke;
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.moveTo(142, 88);
    ctx.lineTo(882, 88);
    ctx.moveTo(142, 180);
    ctx.lineTo(882, 180);
    ctx.stroke();

    ctx.fillStyle = "rgba(246, 255, 248, 0.95)";
    ctx.font = "800 92px Poppins, Arial, sans-serif";
    ctx.fillText("E3 ACCESS", 512, 136);

    ctx.shadowBlur = 12 + 5 * pulse;
    ctx.fillStyle = "rgba(245, 245, 245, 0.94)";
    ctx.font = "700 78px Poppins, Arial, sans-serif";
    ctx.fillText(action.kicker, 512, 296);

    ctx.fillStyle = color.text;
    ctx.font = "800 72px Poppins, Arial, sans-serif";
    ctx.fillText(action.command, 512, 404);

    ctx.restore();
    ctx.shadowBlur = 0;
    ctx.globalAlpha = 1;
    oled.texture.needsUpdate = true;
  }

  function createThumbstick(action) {
    var group = new THREE.Group();
    group.position.set(action.x, -0.58, 0.44);
    group.userData.action = action;

    var recessRing = new THREE.Mesh(
      new THREE.RingGeometry(0.43, 0.465, 96),
      redAccentMaterial.clone()
    );
    recessRing.position.z = 0.028;
    recessRing.renderOrder = 2;
    recessRing.material.opacity = 0.12;
    group.add(recessRing);

    var metalRing = new THREE.Mesh(
      new THREE.RingGeometry(0.382, 0.426, 96),
      gunmetalMaterial.clone()
    );
    metalRing.position.z = 0.178;
    metalRing.renderOrder = 3;
    group.add(metalRing);

    var redUnderRing = new THREE.Mesh(
      new THREE.RingGeometry(0.398, 0.414, 96),
      redAccentMaterial.clone()
    );
    redUnderRing.position.z = 0.172;
    redUnderRing.renderOrder = 4;
    redUnderRing.material.opacity = 0.14;
    group.add(redUnderRing);

    var hoverRing = new THREE.Mesh(
      new THREE.RingGeometry(0.372, 0.386, 96),
      whiteAccentMaterial.clone()
    );
    hoverRing.position.z = 0.205;
    hoverRing.renderOrder = 6;
    hoverRing.material.opacity = 0;
    group.add(hoverRing);

    var stem = new THREE.Mesh(
      new THREE.CylinderGeometry(0.23, 0.26, 0.12, 64),
      blackRubber
    );
    stem.rotation.x = Math.PI / 2;
    stem.position.z = 0.08;
    stem.castShadow = true;
    stem.receiveShadow = true;
    group.add(stem);

    var cap = new THREE.Mesh(
      new THREE.CylinderGeometry(0.35, 0.38, 0.12, 72, 1, false),
      [
        blackRubber,
        new THREE.MeshPhysicalMaterial({
          color: 0x090909,
          roughness: 0.86,
          metalness: 0,
          clearcoat: 0.04,
          clearcoatRoughness: 0.75,
          emissive: new THREE.Color(0x101010),
          emissiveIntensity: 0.08
        }),
        blackRubber
      ]
    );
    cap.rotation.x = Math.PI / 2;
    cap.position.z = 0.12;
    cap.castShadow = true;
    cap.receiveShadow = true;
    group.add(cap);

    var labelTexture = createStickLabelTexture(action.label);
    var surfaceDisc = new THREE.Mesh(
      new THREE.CircleGeometry(0.318, 72),
      new THREE.MeshPhysicalMaterial({
        color: 0x0b0b0b,
        roughness: 0.88,
        metalness: 0,
        clearcoat: 0.04,
        clearcoatRoughness: 0.82,
        depthTest: false,
        depthWrite: false
      })
    );
    surfaceDisc.position.z = 0.214;
    surfaceDisc.renderOrder = 4;
    group.add(surfaceDisc);

    var labelSprite = new THREE.Sprite(
      new THREE.SpriteMaterial({
        map: labelTexture,
        color: 0xffffff,
        transparent: true,
        depthTest: false,
        depthWrite: false,
        opacity: 0.98
      })
    );
    labelSprite.position.z = 0.22;
    labelSprite.renderOrder = 5;
    labelSprite.scale.set(0.78, 0.32, 1);
    group.add(labelSprite);

    interactiveTargets.push(cap, stem);

    return {
      group: group,
      cap: cap,
      recessRing: recessRing,
      metalRing: metalRing,
      redUnderRing: redUnderRing,
      hoverRing: hoverRing,
      surfaceDisc: surfaceDisc,
      labelSprite: labelSprite,
      action: action,
      targetPress: 0,
      press: 0,
      hover: 0
    };
  }

  var leftStick = createThumbstick({
    label: "LOGIN",
    href: loginUrl,
    x: -1.06,
    kicker: "Returning Player",
    command: "\u25ba Secure Login",
    color: {
      fill: "rgba(0, 255, 140, 0.24)",
      stroke: "rgba(88, 255, 174, 0.92)",
      text: "rgba(232, 255, 242, 0.98)",
      hex: 0x58ffae,
      led: 0x58ffae
    }
  });
  var rightStick = createThumbstick({
    label: "JOIN",
    href: joinUrl,
    x: 1.06,
    kicker: "New Member",
    command: "\u25ba Create Account",
    color: {
      fill: "rgba(44, 180, 255, 0.25)",
      stroke: "rgba(99, 207, 255, 0.94)",
      text: "rgba(232, 248, 255, 0.98)",
      hex: 0x63cfff,
      led: 0x63cfff
    }
  });

  controller.add(leftStick.group);
  controller.add(rightStick.group);

  function controllerShape(scale) {
    var s = scale || 1;
    var shape = new THREE.Shape();
    shape.moveTo(-3.95 * s, -0.22 * s);
    shape.bezierCurveTo(-4.5 * s, 0.58 * s, -3.98 * s, 1.7 * s, -2.62 * s, 1.55 * s);
    shape.bezierCurveTo(-1.58 * s, 1.44 * s, -1.1 * s, 1.06 * s, -0.48 * s, 1.1 * s);
    shape.bezierCurveTo(-0.18 * s, 1.14 * s, 0.18 * s, 1.14 * s, 0.48 * s, 1.1 * s);
    shape.bezierCurveTo(1.1 * s, 1.06 * s, 1.58 * s, 1.44 * s, 2.62 * s, 1.55 * s);
    shape.bezierCurveTo(3.98 * s, 1.7 * s, 4.5 * s, 0.58 * s, 3.95 * s, -0.22 * s);
    shape.bezierCurveTo(3.58 * s, -0.78 * s, 3.2 * s, -1.96 * s, 2.05 * s, -2.16 * s);
    shape.bezierCurveTo(1.14 * s, -2.32 * s, 0.9 * s, -1.1 * s, 0.48 * s, -0.9 * s);
    shape.bezierCurveTo(0.2 * s, -0.76 * s, -0.2 * s, -0.76 * s, -0.48 * s, -0.9 * s);
    shape.bezierCurveTo(-0.9 * s, -1.1 * s, -1.14 * s, -2.32 * s, -2.05 * s, -2.16 * s);
    shape.bezierCurveTo(-3.2 * s, -1.96 * s, -3.58 * s, -0.78 * s, -3.95 * s, -0.22 * s);
    return shape;
  }

  var shellGeometry = new THREE.ExtrudeGeometry(controllerShape(1), {
    depth: 0.58,
    bevelEnabled: true,
    bevelThickness: 0.2,
    bevelSize: 0.18,
    bevelSegments: 18,
    curveSegments: 48,
    steps: 1
  });
  shellGeometry.center();
  var shell = new THREE.Mesh(shellGeometry, whitePlastic);
  shell.castShadow = true;
  shell.receiveShadow = true;
  shell.scale.set(1, 0.82, 0.82);
  controller.add(shell);

  var lowerShell = new THREE.Mesh(shellGeometry.clone(), sidePlastic);
  lowerShell.position.z = -0.18;
  lowerShell.scale.set(0.985, 0.805, 0.55);
  lowerShell.castShadow = true;
  lowerShell.receiveShadow = true;
  controller.add(lowerShell);

  function cylinder(radius, height, material, x, y, z, segments) {
    var mesh = new THREE.Mesh(new THREE.CylinderGeometry(radius, radius, height, segments || 64), material);
    mesh.rotation.x = Math.PI / 2;
    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    controller.add(mesh);
    return mesh;
  }

  function roundedRect(width, height, radius) {
    var x = -width / 2;
    var y = -height / 2;
    var shape = new THREE.Shape();
    shape.moveTo(x + radius, y);
    shape.lineTo(x + width - radius, y);
    shape.quadraticCurveTo(x + width, y, x + width, y + radius);
    shape.lineTo(x + width, y + height - radius);
    shape.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
    shape.lineTo(x + radius, y + height);
    shape.quadraticCurveTo(x, y + height, x, y + height - radius);
    shape.lineTo(x, y + radius);
    shape.quadraticCurveTo(x, y, x + radius, y);
    return shape;
  }

  function extrudedButton(width, height, radius, depth, material, x, y, z) {
    var geometry = new THREE.ExtrudeGeometry(roundedRect(width, height, radius), {
      depth: depth,
      bevelEnabled: true,
      bevelThickness: depth * 0.38,
      bevelSize: radius * 0.36,
      bevelSegments: 10,
      curveSegments: 18
    });
    geometry.center();
    var mesh = new THREE.Mesh(geometry, material);
    mesh.position.set(x, y, z);
    mesh.castShadow = true;
    mesh.receiveShadow = true;
    controller.add(mesh);
    return mesh;
  }

  var touchpad = extrudedButton(1.22, 0.5, 0.12, 0.12, glossyBlack.clone(), 0, 0.42, 0.42);
  touchpad.material.emissive = new THREE.Color(0x000000);
  touchpad.material.emissiveIntensity = 0;
  touchpad.rotation.z = 0.01;

  var touchpadTrim = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(roundedRect(1.28, 0.56, 0.14).getPoints(72).map(function (p) {
      return new THREE.Vector3(p.x, p.y, 0);
    })),
    redAccentMaterial.clone()
  );
  touchpadTrim.position.set(0, 0.42, 0.505);
  touchpadTrim.rotation.z = 0.01;
  touchpadTrim.material.opacity = 0.32;
  touchpadTrim.renderOrder = 7;
  controller.add(touchpadTrim);

  var touchpadLogoMark = null;
  if (touchpadLogoUrl) {
    textureLoader.load(touchpadLogoUrl, function (texture) {
      texture.colorSpace = THREE.SRGBColorSpace;
      texture.anisotropy = Math.min(renderer.capabilities.getMaxAnisotropy(), 8);
      texture.needsUpdate = true;

      touchpadLogoMark = new THREE.Mesh(
        new THREE.PlaneGeometry(0.62, 0.076),
        new THREE.MeshBasicMaterial({
          map: texture,
          color: 0xdedede,
          transparent: true,
          opacity: 0,
          depthTest: false,
          depthWrite: false,
          toneMapped: false
        })
      );
      touchpadLogoMark.position.set(0, 0.42, 0.502);
      touchpadLogoMark.rotation.z = 0.01;
      touchpadLogoMark.renderOrder = 6;
      controller.add(touchpadLogoMark);
    });
  }

  var oled = createOledTexture();
  var oledDisplay = new THREE.Mesh(
    new THREE.PlaneGeometry(1.02, 0.38),
    new THREE.MeshBasicMaterial({
      map: oled.texture,
      transparent: true,
      opacity: 0,
      depthWrite: false,
      toneMapped: false
    })
  );
  oledDisplay.position.set(0, 0.42, 0.505);
  oledDisplay.rotation.z = 0.01;
  oledDisplay.renderOrder = 8;
  controller.add(oledDisplay);

  extrudedButton(0.26, 0.12, 0.045, 0.08, glossyBlack, -0.82, 0.34, 0.47);
  extrudedButton(0.26, 0.12, 0.045, 0.08, glossyBlack, 0.82, 0.34, 0.47);
  cylinder(0.1, 0.09, glossyBlack, 0, -0.08, 0.5, 32);

  var dpadBarA = extrudedButton(0.28, 1.05, 0.075, 0.13, blackRubber, -2.56, 0.03, 0.53);
  var dpadBarB = extrudedButton(1.05, 0.28, 0.075, 0.13, blackRubber, -2.56, 0.03, 0.55);
  dpadBarA.material = dpadMaterial.clone();
  dpadBarB.material = dpadMaterial.clone();
  dpadBarA.rotation.z = 0.002;
  dpadBarB.rotation.z = 0.002;
  dpadBarA.userData.decorative = "dpad";
  dpadBarB.userData.decorative = "dpad";
  decorativeTargets.push(dpadBarA, dpadBarB);
  var dpadEdge = new THREE.Mesh(
    new THREE.RingGeometry(0.58, 0.59, 96),
    whiteAccentMaterial.clone()
  );
  dpadEdge.scale.set(1.12, 1.12, 1);
  dpadEdge.position.set(-2.56, 0.03, 0.625);
  dpadEdge.material.opacity = 0.045;
  dpadEdge.renderOrder = 3;
  controller.add(dpadEdge);
  var dpadRedPulse = new THREE.Mesh(
    new THREE.RingGeometry(0.55, 0.585, 96),
    redAccentMaterial.clone()
  );
  dpadRedPulse.scale.set(1.08, 1.08, 1);
  dpadRedPulse.position.set(-2.56, 0.03, 0.615);
  dpadRedPulse.material.opacity = 0;
  dpadRedPulse.renderOrder = 2;
  controller.add(dpadRedPulse);
  var dpadState = { hover: 0, press: 0 };
  var dpadArrows = [];
  [
    [-2.56, 0.44, "\u2191"],
    [-2.56, -0.38, "\u2193"],
    [-2.98, 0.03, "\u2190"],
    [-2.14, 0.03, "\u2192"]
  ].forEach(function (item) {
    var arrow = new THREE.Mesh(
      new THREE.PlaneGeometry(0.31, 0.31),
      new THREE.MeshBasicMaterial({
        map: createDpadArrowTexture(item[2]),
        transparent: true,
        opacity: 0.82,
        depthTest: false,
        depthWrite: false,
        toneMapped: false
      })
    );
    arrow.position.set(item[0], item[1], 0.695);
    arrow.renderOrder = 14;
    controller.add(arrow);
    dpadArrows.push(arrow);
  });

  var dpadLocalLight = new THREE.PointLight(BRAND.legendRed, 0.035, 1.25);
  dpadLocalLight.position.set(-2.56, 0.03, 0.82);
  controller.add(dpadLocalLight);

  var faceButtons = [];
  [[2.62, 0.42, "\u25b3"], [3.07, 0.03, "\u25cb"], [2.17, 0.03, "\u25a1"], [2.62, -0.36, "\u00d7"]].forEach(function (position) {
    var ring = new THREE.Mesh(
      new THREE.RingGeometry(0.232, 0.266, 64),
      gunmetalMaterial.clone()
    );
    ring.position.set(position[0], position[1], 0.545);
    ring.renderOrder = 2;
    controller.add(ring);

    var edge = new THREE.Mesh(
      new THREE.RingGeometry(0.218, 0.224, 64),
      whiteAccentMaterial.clone()
    );
    edge.position.set(position[0], position[1], 0.635);
    edge.material.opacity = 0.055;
    edge.renderOrder = 5;
    controller.add(edge);

    var button = cylinder(0.22, 0.15, faceButtonMaterial.clone(), position[0], position[1], 0.55, 56);
    button.userData.decorative = "face";
    button.userData.faceIndex = faceButtons.length;
    decorativeTargets.push(button);

    var legend = new THREE.Mesh(
      new THREE.PlaneGeometry(0.285, 0.285),
      new THREE.MeshBasicMaterial({
        map: createFaceSymbolTexture(position[2]),
        transparent: true,
        opacity: 0.86,
        depthWrite: false,
        toneMapped: false
      })
    );
    legend.position.set(position[0], position[1], 0.633);
    legend.renderOrder = 6;
    controller.add(legend);

    faceButtons.push({ button: button, ring: ring, edge: edge, legend: legend, hover: 0 });
  });

  var seamPoints = controllerShape(0.84).getPoints(160).map(function (p) {
    return new THREE.Vector3(p.x, p.y * 0.82, 0.51);
  });
  var seamGeometry = new THREE.BufferGeometry().setFromPoints(seamPoints);
  var seam = new THREE.LineLoop(seamGeometry, seamMaterial);
  controller.add(seam);

  var shellBreakPoints = controllerShape(0.94).getPoints(160).map(function (p) {
    return new THREE.Vector3(p.x, p.y * 0.82 - 0.025, 0.485);
  });
  var shellBreak = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(shellBreakPoints),
    new THREE.LineBasicMaterial({
      color: BRAND.black,
      transparent: true,
      opacity: 0.42
    })
  );
  controller.add(shellBreak);

  var rimLightPoints = controllerShape(1.012).getPoints(180).map(function (p) {
    return new THREE.Vector3(p.x, p.y * 0.82, 0.565);
  });
  var rimLightLine = new THREE.LineLoop(
    new THREE.BufferGeometry().setFromPoints(rimLightPoints),
    new THREE.LineBasicMaterial({
      color: BRAND.white,
      transparent: true,
      opacity: 0.095
    })
  );
  controller.add(rimLightLine);

  var topEdgeLight = new THREE.Mesh(
    new THREE.PlaneGeometry(4.35, 0.055),
    new THREE.MeshBasicMaterial({
      color: BRAND.white,
      transparent: true,
      opacity: 0.09,
      depthWrite: false
    })
  );
  topEdgeLight.position.set(0, 1.54, 0.61);
  topEdgeLight.rotation.z = -0.004;
  controller.add(topEdgeLight);

  var ethreeMark = new THREE.Mesh(
    new THREE.PlaneGeometry(0.42, 0.08),
    new THREE.MeshBasicMaterial({
      map: createEngravedTextTexture("ETHREE", 420, 90, 38, 45),
      transparent: true,
      opacity: 0.2,
      depthWrite: false,
      toneMapped: false
    })
  );
  ethreeMark.position.set(0, 0.04, 0.602);
  ethreeMark.renderOrder = 5;
  controller.add(ethreeMark);

  var statusLed = new THREE.Mesh(
    new THREE.CircleGeometry(0.035, 32),
    new THREE.MeshBasicMaterial({
      color: BRAND.white,
      transparent: true,
      opacity: 0.76,
      depthWrite: false,
      toneMapped: false
    })
  );
  statusLed.position.set(0, -0.08, 0.606);
  statusLed.renderOrder = 6;
  controller.add(statusLed);
  var statusLedGlow = new THREE.Mesh(
    new THREE.CircleGeometry(0.075, 32),
    new THREE.MeshBasicMaterial({
      color: BRAND.white,
      transparent: true,
      opacity: 0.08,
      depthWrite: false,
      toneMapped: false
    })
  );
  statusLedGlow.position.set(0, -0.08, 0.604);
  statusLedGlow.renderOrder = 5;
  controller.add(statusLedGlow);

  var highlight = new THREE.Mesh(
    new THREE.PlaneGeometry(3.8, 0.18),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.045, depthWrite: false })
  );
  highlight.position.set(-0.42, 0.96, 0.58);
  highlight.rotation.z = -0.035;
  controller.add(highlight);

  var contactShadow = new THREE.Mesh(
    new THREE.CircleGeometry(2.75, 96),
    new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.54, depthWrite: false })
  );
  contactShadow.scale.set(1.48, 0.15, 1);
  contactShadow.position.set(0, -2.35, -0.96);
  scene.add(contactShadow);

  var floorReflection = new THREE.Mesh(
    new THREE.CircleGeometry(2.45, 96),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.052, depthWrite: false })
  );
  floorReflection.scale.set(1.48, 0.105, 1);
  floorReflection.position.set(0, -2.16, -0.94);
  scene.add(floorReflection);

  var floorSheen = new THREE.Mesh(
    new THREE.PlaneGeometry(5.8, 0.05),
    new THREE.MeshBasicMaterial({ color: 0xffffff, transparent: true, opacity: 0.035, depthWrite: false })
  );
  floorSheen.position.set(0, -2.02, -0.935);
  scene.add(floorSheen);

  var ambientShadow = new THREE.Mesh(
    new THREE.CircleGeometry(3.25, 96),
    new THREE.MeshBasicMaterial({ color: 0x000000, transparent: true, opacity: 0.2, depthWrite: false })
  );
  ambientShadow.scale.set(1.55, 0.23, 1);
  ambientShadow.position.set(0, -2.3, -0.98);
  scene.add(ambientShadow);

  var ambient = new THREE.AmbientLight(0xffffff, 0.1);
  scene.add(ambient);

  var key = new THREE.DirectionalLight(0xffffff, 3.55);
  key.position.set(4.2, 4.5, 6.5);
  key.castShadow = true;
  key.shadow.mapSize.set(1024, 1024);
  scene.add(key);

  var fill = new THREE.DirectionalLight(BRAND.ash, 0.58);
  fill.position.set(-5, 2, 4.5);
  scene.add(fill);

  var rim = new THREE.DirectionalLight(0xffffff, 3.15);
  rim.position.set(0, 2.8, -5.8);
  scene.add(rim);

  var glint = new THREE.PointLight(0xffffff, 1.55, 18);
  glint.position.set(-2.5, 1.4, 3.6);
  scene.add(glint);

  var target = { x: 0, y: 0 };
  var rotation = { x: 0, y: 0 };
  var maxRotation = THREE.MathUtils.degToRad(12);
  var idleClock = new THREE.Clock();

  function startOledSequence(action) {
    if (launchTimer) {
      window.clearTimeout(launchTimer);
      launchTimer = 0;
    }
    if (oledTimer) {
      window.clearTimeout(oledTimer);
      oledTimer = 0;
    }

    oledState.active = true;
    oledState.fading = false;
    oledState.startedAt = idleClock.getElapsedTime();
    oledState.fadeStartedAt = 0;
    oledState.action = action;
    oledState.opacity = 0;
    drawOledDisplay(oled, action, 0, 0);

    oledTimer = window.setTimeout(function () {
      oledState.fading = true;
      oledState.fadeStartedAt = idleClock.getElapsedTime();
      launchTimer = window.setTimeout(function () {
        oledTimer = 0;
        launchTimer = 0;
        navigateStick(action);
      }, 240);
    }, 720);
  }

  function updatePointer(clientX, clientY) {
    target.y = THREE.MathUtils.clamp((clientX / window.innerWidth - 0.5) * 2, -1, 1);
    target.x = THREE.MathUtils.clamp((clientY / window.innerHeight - 0.5) * 2, -1, 1);
  }

  function getStickFromHit(hit) {
    var object = hit;
    while (object) {
      if (object.userData && object.userData.action) return object.userData.action;
      object = object.parent;
    }
    return null;
  }

  function getDecorativeFromHit(hit) {
    var object = hit;
    while (object) {
      if (object.userData && object.userData.decorative) {
        return {
          type: object.userData.decorative,
          index: object.userData.faceIndex
        };
      }
      object = object.parent;
    }
    return null;
  }

  function updateHoverState() {
    raycaster.setFromCamera(pointer, camera);
    var hits = raycaster.intersectObjects(interactiveTargets, false);
    var nextHover = hits.length ? getStickFromHit(hits[0].object) : null;
    var decorativeHits = nextHover ? [] : raycaster.intersectObjects(decorativeTargets, false);
    hoveredDecorative = decorativeHits.length ? getDecorativeFromHit(decorativeHits[0].object) : null;

    if (nextHover !== hoveredStick) {
      hoveredStick = nextHover;
      mount.style.cursor = hoveredStick ? "pointer" : "default";
    }

    [leftStick, rightStick].forEach(function (stick) {
      var isHover = hoveredStick && hoveredStick.href === stick.action.href;
      stick.targetPress = activeStick && activeStick.href === stick.action.href ? 1 : 0;
      stick.hover = isHover ? 1 : 0;
    });

    if (!hoveredStick && hoveredDecorative) {
      mount.style.cursor = "default";
    }
  }

  function navigateStick(stick) {
    if (!stick) return;
    window.location.href = stick.href;
  }

  mount.addEventListener("pointermove", function (event) {
    updatePointer(event.clientX, event.clientY);
    pointer.set((event.clientX / window.innerWidth) * 2 - 1, -(event.clientY / window.innerHeight) * 2 + 1);
    updateHoverState();
  }, { passive: true });

  mount.addEventListener("pointerleave", function () {
    activeStick = null;
    hoveredStick = null;
    activeDecorative = null;
    hoveredDecorative = null;
    mount.style.cursor = "default";
    leftStick.hover = 0;
    rightStick.hover = 0;
    leftStick.targetPress = activeStick && activeStick.href === leftStick.action.href ? 1 : 0;
    rightStick.targetPress = activeStick && activeStick.href === rightStick.action.href ? 1 : 0;
  });

  mount.addEventListener("pointerdown", function (event) {
    pointer.set((event.clientX / window.innerWidth) * 2 - 1, -(event.clientY / window.innerHeight) * 2 + 1);
    raycaster.setFromCamera(pointer, camera);
    var hits = raycaster.intersectObjects(interactiveTargets, false);
    var hitAction = hits.length ? getStickFromHit(hits[0].object) : null;
    if (!hitAction) {
      var decorativeHits = raycaster.intersectObjects(decorativeTargets, false);
      activeDecorative = decorativeHits.length ? getDecorativeFromHit(decorativeHits[0].object) : null;
      updateHoverState();
      return;
    }
    if (launchTimer) {
      window.clearTimeout(launchTimer);
      launchTimer = 0;
    }
    if (oledTimer) {
      window.clearTimeout(oledTimer);
      oledTimer = 0;
    }
    oledState.active = false;
    oledState.fading = false;
    activeStick = hitAction;
    activeDecorative = null;
    updateHoverState();
  });

  window.addEventListener("pointerup", function () {
    if (activeStick && hoveredStick && activeStick.href === hoveredStick.href) {
      startOledSequence(activeStick);
    }
    activeStick = null;
    activeDecorative = null;
    updateHoverState();
  });

  function resize() {
    var rect = mount.getBoundingClientRect();
    var width = Math.max(1, rect.width);
    var height = Math.max(1, rect.height);
    renderer.setSize(width, height, false);
    camera.aspect = width / height;
    camera.position.z = width < 560 ? 16 : width < 900 ? 13.2 : 10.5;
    controller.scale.setScalar(width < 560 ? 0.48 : width < 900 ? 0.72 : 1);
    camera.updateProjectionMatrix();
  }

  window.addEventListener("resize", resize, { passive: true });
  resize();

  function animate() {
    var elapsed = idleClock.getElapsedTime();
    var idleY = Math.sin(elapsed * 0.36) * THREE.MathUtils.degToRad(1.7);
    var idleX = Math.sin(elapsed * 0.29 + 0.8) * THREE.MathUtils.degToRad(1.1);
    var float = prefersReducedMotion ? 0 : Math.sin(elapsed * 0.82) * 0.09;

    rotation.y += ((target.y * maxRotation) + idleY - rotation.y) * 0.075;
    rotation.x += ((target.x * maxRotation) + idleX - rotation.x) * 0.075;

    controller.rotation.y = rotation.y;
    controller.rotation.x = -0.18 + rotation.x;
    controller.rotation.z = Math.sin(elapsed * 0.22) * THREE.MathUtils.degToRad(1.2);
    controller.position.y = float;
    contactShadow.position.y = -2.35 + float * 0.25;
    contactShadow.material.opacity = 0.5 + Math.sin(elapsed * 0.82 + 1.2) * 0.035;
    floorReflection.position.y = -2.18 + float * 0.18;
    floorReflection.material.opacity = 0.035 + Math.max(0, Math.sin(elapsed * 0.82 + 0.4)) * 0.012;
    ambientShadow.position.y = -2.3 + float * 0.14;

    if (oledState.active && oledState.action) {
      var oledElapsed = elapsed - oledState.startedAt;
      var fadeIn = THREE.MathUtils.smoothstep(Math.min(oledElapsed / 0.26, 1), 0, 1);
      var fadeOut = oledState.fading
        ? 1 - THREE.MathUtils.smoothstep(Math.min((elapsed - oledState.fadeStartedAt) / 0.24, 1), 0, 1)
        : 1;
      var pulse = 0.5 + Math.sin(elapsed * 14) * 0.5;
      var oledOpacity = fadeIn * fadeOut;

      drawOledDisplay(oled, oledState.action, oledElapsed, pulse);
      oledDisplay.material.opacity = oledOpacity;
      oledDisplay.scale.set(1, 0.82 + 0.18 * fadeIn, 1);
      if (touchpadLogoMark) {
        touchpadLogoMark.material.opacity = 0.13 + 0.27 * oledOpacity;
      }
      touchpad.material.emissive.setHex(oledState.action.color.hex);
      touchpad.material.emissiveIntensity = 0.04 * oledOpacity + 0.015 * pulse * oledOpacity;
      statusLed.material.color.setHex(oledState.fading ? BRAND.red : oledState.action.color.led);
      statusLedGlow.material.color.setHex(oledState.fading ? BRAND.red : oledState.action.color.led);
      statusLed.material.opacity = oledState.fading ? 0.5 + 0.18 * pulse : 0.82;
      statusLedGlow.material.opacity = oledState.fading ? 0.16 + 0.08 * pulse : 0.11;
      if (oledState.fading && fadeOut <= 0.02) {
        oledState.active = false;
      }
    } else {
      oledDisplay.material.opacity = 0;
      if (touchpadLogoMark) {
        touchpadLogoMark.material.opacity = 0.035 + Math.max(0, Math.sin(elapsed * 0.7)) * 0.045;
      }
      touchpad.material.emissiveIntensity = 0;
      statusLed.material.color.setHex(BRAND.white);
      statusLedGlow.material.color.setHex(BRAND.white);
      statusLed.material.opacity = 0.58;
      statusLedGlow.material.opacity = 0.055 + Math.max(0, Math.sin(elapsed * 1.1)) * 0.018;
    }

    [leftStick, rightStick].forEach(function (stick) {
      stick.hover = THREE.MathUtils.lerp(stick.hover, hoveredStick && hoveredStick.href === stick.action.href ? 1 : 0, 0.12);
      stick.press = THREE.MathUtils.lerp(stick.press, stick.targetPress, 0.18);

      var pressOffset = -0.045 * stick.press;
      var hoverLift = 0.008 * stick.hover;
      stick.group.position.z = 0.44 + pressOffset + hoverLift;
      stick.surfaceDisc.scale.setScalar(1 - 0.018 * stick.press);
      stick.labelSprite.material.opacity = 0.96 + 0.04 * stick.hover;
      stick.labelSprite.scale.set(0.78 - 0.03 * stick.press, 0.32 - 0.012 * stick.press, 1);
      stick.cap.scale.setScalar(1 - 0.02 * stick.press);
      stick.cap.material[1].emissiveIntensity = 0.08 + 0.04 * stick.hover;
      stick.cap.material[1].roughness = 0.86 + 0.04 * stick.press;
      stick.hoverRing.material.opacity = 0.02 + 0.32 * stick.hover;
      stick.hoverRing.scale.setScalar(1 + 0.025 * stick.hover - 0.018 * stick.press);
      stick.recessRing.material.opacity = 0.12 + 0.16 * stick.hover + 0.52 * stick.press;
      stick.recessRing.scale.setScalar(1 + 0.02 * stick.press);
      stick.metalRing.scale.setScalar(1 + 0.018 * stick.hover - 0.012 * stick.press);
      stick.metalRing.material.emissive = stick.metalRing.material.emissive || new THREE.Color(0x000000);
      stick.metalRing.material.emissive.setHex(BRAND.white);
      stick.metalRing.material.emissiveIntensity = 0.006 + 0.018 * stick.hover;
      stick.redUnderRing.material.opacity = 0.12 + 0.08 * stick.hover + 0.32 * stick.press;
      stick.redUnderRing.scale.setScalar(1 + 0.025 * stick.press);
    });

    faceButtons.forEach(function (entry, index) {
      var isHover = hoveredDecorative && hoveredDecorative.type === "face" && hoveredDecorative.index === index;
      var isPress = activeDecorative && activeDecorative.type === "face" && activeDecorative.index === index;
      entry.hover = THREE.MathUtils.lerp(entry.hover, isHover ? 1 : 0, 0.14);
      var press = isPress ? 1 : 0;
      entry.ring.material.emissive = entry.ring.material.emissive || new THREE.Color(0x000000);
      entry.ring.material.emissive.setHex(BRAND.white);
      entry.ring.material.emissiveIntensity = 0.006 + 0.025 * entry.hover;
      entry.ring.scale.setScalar(1 + 0.045 * entry.hover + 0.08 * press);
      entry.edge.material.opacity = 0.065 + 0.16 * entry.hover;
      entry.legend.material.opacity = 0.82 + 0.08 * entry.hover + 0.1 * press;
      entry.legend.scale.setScalar(1 - 0.018 * press);
      entry.button.position.z = 0.55 - 0.018 * press + 0.008 * entry.hover;
      entry.button.material.emissive = entry.button.material.emissive || new THREE.Color(0x000000);
      entry.button.material.emissive.setHex(BRAND.white);
      entry.button.material.emissiveIntensity = 0.012 * entry.hover + 0.008 * press;
    });

    var dpadHoverTarget = hoveredDecorative && hoveredDecorative.type === "dpad" ? 1 : 0;
    var dpadPressTarget = activeDecorative && activeDecorative.type === "dpad" ? 1 : 0;
    dpadState.hover = THREE.MathUtils.lerp(dpadState.hover, dpadHoverTarget, 0.14);
    dpadState.press = THREE.MathUtils.lerp(dpadState.press, dpadPressTarget, 0.18);
    dpadEdge.material.opacity = 0.045 + 0.24 * dpadState.hover;
    dpadEdge.scale.setScalar(1.12 + 0.035 * dpadState.hover);
    dpadRedPulse.material.opacity = 0.02 * dpadState.hover + 0.48 * dpadState.press;
    dpadRedPulse.scale.setScalar(1.08 + 0.08 * dpadState.press);
    dpadBarA.position.z = 0.53 - 0.016 * dpadState.press + 0.006 * dpadState.hover;
    dpadBarB.position.z = 0.55 - 0.016 * dpadState.press + 0.006 * dpadState.hover;
    dpadBarA.material.emissive = dpadBarA.material.emissive || new THREE.Color(0x000000);
    dpadBarB.material.emissive = dpadBarB.material.emissive || new THREE.Color(0x000000);
    dpadBarA.material.emissive.setHex(dpadState.press > 0.08 ? BRAND.red : BRAND.white);
    dpadBarB.material.emissive.setHex(dpadState.press > 0.08 ? BRAND.red : BRAND.white);
    dpadBarA.material.emissiveIntensity = 0.012 * dpadState.hover + 0.04 * dpadState.press;
    dpadBarB.material.emissiveIntensity = 0.012 * dpadState.hover + 0.04 * dpadState.press;
    dpadArrows.forEach(function (arrow) {
      arrow.material.opacity = 0.78 + 0.05 * dpadState.hover + 0.08 * dpadState.press;
      arrow.scale.setScalar(1 - 0.025 * dpadState.press);
      arrow.position.z = 0.695 - 0.012 * dpadState.press + 0.002 * dpadState.hover;
    });
    dpadLocalLight.intensity = 0.035 + 0.012 * dpadState.hover + 0.018 * dpadState.press;

    touchpadTrim.material.opacity = oledState.active ? 0.18 : 0.045 + Math.sin(elapsed * 1.8) * 0.012;
    rimLightLine.material.opacity = 0.1 + Math.max(0, Math.sin(elapsed * 0.5 + 0.8)) * 0.06;
    shellBreak.material.opacity = 0.48 + Math.max(0, Math.sin(elapsed * 0.42)) * 0.08;
    highlight.material.opacity = 0.032 + Math.sin(elapsed * 0.7) * 0.012;
    highlight.position.x = -0.42 + Math.sin(elapsed * 0.36) * 0.08;
    topEdgeLight.material.opacity = 0.07 + Math.max(0, Math.sin(elapsed * 0.45 + 0.4)) * 0.035;
    floorSheen.material.opacity = 0.025 + Math.max(0, Math.sin(elapsed * 0.6 + 1.2)) * 0.014;

    renderer.render(scene, camera);
    requestAnimationFrame(animate);
  }

  animate();
}());

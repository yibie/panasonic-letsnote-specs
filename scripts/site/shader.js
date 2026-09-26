(() => {
  /* ---------- Glass-case reflection shader ----------
     One shared WebGL canvas renders every visible case, then copies the
     result into that case's own 2D canvas. The laptop gets a moving specular
     band and a thin glint; the white/transparent backdrop is masked out. */
  const reduceMotion = matchMedia("(prefers-reduced-motion: reduce)").matches;
  const glCanvas = document.createElement("canvas");
  const gl = glCanvas.getContext("webgl", { premultipliedAlpha: false, alpha: true, antialias: false });
  const cases = [...document.querySelectorAll(".vitrine")].filter(v => v.querySelector("img"));
  const pointer = { x: -1, y: -1, t: 0 };
  addEventListener("pointermove", e => { pointer.x = e.clientX; pointer.y = e.clientY; pointer.t = performance.now(); }, { passive: true });

  function setGlassSheen(now) {
    // CSS glass sheen on every visible case; also the fallback without WebGL.
    for (const v of visible) {
      const r = v.getBoundingClientRect();
      v.style.setProperty("--lx", (lightFor(r, now).x * 100).toFixed(1) + "%");
    }
  }

  function lightFor(r, now) {
    // Follow the pointer while it moves; otherwise sweep with scroll position.
    if (now - pointer.t < 2500 && pointer.x >= 0) {
      return { x: (pointer.x - r.left) / r.width, y: (pointer.y - r.top) / r.height };
    }
    const drift = reduceMotion ? 0 : Math.sin(now / 2600 + r.left / 300) * 0.12;
    return { x: 1.15 - (r.top + r.height / 2) / innerHeight * 1.3 + drift, y: 0.35 };
  }

  const visible = new Set();
  const io = new IntersectionObserver(entries => {
    for (const e of entries) e.isIntersecting ? visible.add(e.target) : visible.delete(e.target);
  }, { rootMargin: "120px" });
  document.querySelectorAll(".vitrine").forEach(v => io.observe(v));

  if (!gl) {
    const loop = now => { setGlassSheen(now); requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
    return;
  }

  const VS = `attribute vec2 p; varying vec2 uv;
    void main(){ uv = p * .5 + .5; gl_Position = vec4(p, 0., 1.); }`;
  const FS = `precision mediump float;
    varying vec2 uv; uniform sampler2D tex; uniform vec2 light; uniform float time;
    void main(){
      vec4 c = texture2D(tex, uv);
      float lum = dot(c.rgb, vec3(.299, .587, .114));
      // The product, not the white studio backdrop or transparent pixels.
      float backdrop = smoothstep(.88, .97, min(c.r, min(c.g, c.b)));
      float mask = c.a * (1. - backdrop);
      vec2 dir = normalize(vec2(1., -.62));
      float d = dot(uv - light, dir);
      float band = exp(-d * d * 60.);
      float glint = exp(-pow(d + .085, 2.) * 1400.) * .9;
      float ripple = .04 * sin(uv.y * 40. + time * .6);        // faint waviness of old glass
      float spec = (band * .26 + glint * .7) * mask * (.5 + .4 * lum) * (1. + ripple);
      // Brushed-metal feel: brighter surfaces pick up a warmer highlight.
      vec3 col = c.rgb + spec * vec3(1., .97, .9);
      // Slight lift on edges facing the light, like a lid catching it.
      float edge = smoothstep(.0, .6, 1. - abs(d) * 1.4) * mask * .05;
      // Key out the white studio backdrop so the laptop stands in the case.
      float keyed = c.a * (1. - smoothstep(.975, .998, min(c.r, min(c.g, c.b))));
      gl_FragColor = vec4(min(col + edge, 1.), keyed);
    }`;
  function shader(type, src) {
    const s = gl.createShader(type); gl.shaderSource(s, src); gl.compileShader(s);
    if (!gl.getShaderParameter(s, gl.COMPILE_STATUS)) throw new Error(gl.getShaderInfoLog(s));
    return s;
  }
  const prog = gl.createProgram();
  gl.attachShader(prog, shader(gl.VERTEX_SHADER, VS));
  gl.attachShader(prog, shader(gl.FRAGMENT_SHADER, FS));
  gl.linkProgram(prog); gl.useProgram(prog);
  const buf = gl.createBuffer();
  gl.bindBuffer(gl.ARRAY_BUFFER, buf);
  gl.bufferData(gl.ARRAY_BUFFER, new Float32Array([-1, -1, 1, -1, -1, 1, 1, 1]), gl.STATIC_DRAW);
  const loc = gl.getAttribLocation(prog, "p");
  gl.enableVertexAttribArray(loc); gl.vertexAttribPointer(loc, 2, gl.FLOAT, false, 0, 0);
  const uLight = gl.getUniformLocation(prog, "light");
  const uTime = gl.getUniformLocation(prog, "time");
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL, true);
  gl.clearColor(0, 0, 0, 0);

  const state = new Map(); // vitrine -> {img, canvas, ctx, tex}
  function prepare(v) {
    let s = state.get(v);
    if (s) return s;
    const img = v.querySelector("img");
    if (!img.complete || !img.naturalWidth) return null;
    const canvas = v.querySelector("canvas.glass");
    const tex = gl.createTexture();
    gl.bindTexture(gl.TEXTURE_2D, tex);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_MIN_FILTER, gl.LINEAR);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_S, gl.CLAMP_TO_EDGE);
    gl.texParameteri(gl.TEXTURE_2D, gl.TEXTURE_WRAP_T, gl.CLAMP_TO_EDGE);
    try { gl.texImage2D(gl.TEXTURE_2D, 0, gl.RGBA, gl.RGBA, gl.UNSIGNED_BYTE, img); }
    catch (e) { return null; }
    s = { img, canvas, ctx: canvas.getContext("2d"), tex };
    state.set(v, s);
    v.classList.add("gl");
    return s;
  }

  function render(now) {
    setGlassSheen(now);
    const dpr = Math.min(devicePixelRatio || 1, 1.5);
    for (const v of visible) {
      const s = prepare(v);
      if (!s) continue;
      // Place the canvas exactly over the (hidden) image.
      const w = s.img.offsetWidth, h = s.img.offsetHeight;
      if (!w || !h) continue;
      Object.assign(s.canvas.style, { left: s.img.offsetLeft + "px", top: s.img.offsetTop + "px", width: w + "px", height: h + "px" });
      const pw = Math.round(w * dpr), ph = Math.round(h * dpr);
      if (s.canvas.width !== pw || s.canvas.height !== ph) { s.canvas.width = pw; s.canvas.height = ph; }
      if (glCanvas.width < pw || glCanvas.height < ph) { glCanvas.width = Math.max(glCanvas.width, pw); glCanvas.height = Math.max(glCanvas.height, ph); }

      const r = s.img.getBoundingClientRect();
      const l = lightFor(r, now);
      gl.viewport(0, 0, pw, ph);
      gl.clear(gl.COLOR_BUFFER_BIT);
      gl.bindTexture(gl.TEXTURE_2D, s.tex);
      gl.uniform2f(uLight, l.x, 1 - l.y);
      gl.uniform1f(uTime, reduceMotion ? 0 : now / 1000);
      gl.drawArrays(gl.TRIANGLE_STRIP, 0, 4);
      s.ctx.clearRect(0, 0, pw, ph);
      s.ctx.drawImage(glCanvas, 0, glCanvas.height - ph, pw, ph, 0, 0, pw, ph);
    }
    requestAnimationFrame(render);
  }
  requestAnimationFrame(render);
})();

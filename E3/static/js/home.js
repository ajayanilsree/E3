(function () {
  var splash = document.querySelector("[data-e3-splash]");
  var reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  if (splash) {
    document.body.classList.add("e3-splash-running");

    var splashStartedAt = performance.now();
    var minSplashTime = reducedMotion ? 600 : 2300;
    var maxSplashTime = reducedMotion ? 900 : 3000;
    var splashDone = false;

    function revealSplash() {
      if (splashDone) return;
      splashDone = true;

      document.body.classList.add("e3-splash-revealing");
      splash.classList.add("is-leaving");

      window.setTimeout(function () {
        splash.remove();
        document.body.classList.remove("e3-splash-running", "e3-splash-revealing");
      }, reducedMotion ? 220 : 640);
    }

    function scheduleSplashReveal() {
      var elapsed = performance.now() - splashStartedAt;
      window.setTimeout(revealSplash, Math.max(0, minSplashTime - elapsed));
    }

    if (document.readyState === "complete") {
      scheduleSplashReveal();
    } else {
      window.addEventListener("load", scheduleSplashReveal, { once: true });
      window.setTimeout(revealSplash, maxSplashTime);
    }
  }

  var scrollIndicator = document.querySelector("[data-scroll-indicator]");
  var nextSection = document.querySelector("#experiences");
  var homeLogo = document.querySelector("[data-home-logo]");

  if (homeLogo) {
    homeLogo.addEventListener("click", function (event) {
      event.preventDefault();
      window.scrollTo({
        top: 0,
        behavior: reducedMotion ? "auto" : "smooth"
      });
    });
  }

  if (scrollIndicator) {
    function updateScrollIndicator() {
      scrollIndicator.classList.toggle("is-hidden", window.scrollY > 100);
    }

    scrollIndicator.addEventListener("click", function () {
      if (!nextSection) return;
      nextSection.scrollIntoView({
        behavior: reducedMotion ? "auto" : "smooth",
        block: "start"
      });
    });

    window.addEventListener("scroll", updateScrollIndicator, { passive: true });
    updateScrollIndicator();
  }

  var reveals = document.querySelectorAll(".reveal");
  var canObserve = "IntersectionObserver" in window;

  if (!canObserve) {
    reveals.forEach(function (item) {
      item.classList.add("in-view");
    });
  } else {
    var revealObserver = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var delay = entry.target.getAttribute("data-delay") || 0;
        window.setTimeout(function () {
          entry.target.classList.add("in-view");
        }, delay);
        revealObserver.unobserve(entry.target);
      });
    }, { threshold: 0.14 });

    reveals.forEach(function (item) {
      revealObserver.observe(item);
    });
  }

  var hero = document.querySelector("[data-luxury-hero]");
  if (hero && !reducedMotion) {
    var targetX = 0;
    var targetY = 0;
    var currentX = 0;
    var currentY = 0;
    var targetDepth = 0;
    var currentDepth = 0;
    var frameQueued = false;

    function clamp(value, min, max) {
      return Math.min(Math.max(value, min), max);
    }

    function updateHeroDepth() {
      var rect = hero.getBoundingClientRect();
      var viewHeight = window.innerHeight || document.documentElement.clientHeight;
      var progress = 1 - (rect.bottom / Math.max(rect.height, viewHeight));
      targetDepth = clamp(progress * 1.25, 0, 1);
    }

    function renderHero() {
      frameQueued = false;

      currentX += (targetX - currentX) * 0.08;
      currentY += (targetY - currentY) * 0.08;
      currentDepth += (targetDepth - currentDepth) * 0.05;

      hero.style.setProperty("--hero-x", currentX.toFixed(4));
      hero.style.setProperty("--hero-y", currentY.toFixed(4));
      hero.style.setProperty("--hero-depth", currentDepth.toFixed(4));

      if (
        Math.abs(targetX - currentX) > 0.001 ||
        Math.abs(targetY - currentY) > 0.001 ||
        Math.abs(targetDepth - currentDepth) > 0.001
      ) {
        queueHeroFrame();
      }
    }

    function queueHeroFrame() {
      if (frameQueued) return;
      frameQueued = true;
      window.requestAnimationFrame(renderHero);
    }

    hero.addEventListener("pointermove", function (event) {
      var x = event.clientX / Math.max(window.innerWidth, 1);
      var y = event.clientY / Math.max(window.innerHeight, 1);
      targetX = clamp((x - 0.5) * 2, -1, 1);
      targetY = clamp((y - 0.5) * 2, -1, 1);
      queueHeroFrame();
    }, { passive: true });

    hero.addEventListener("pointerleave", function () {
      targetX = 0;
      targetY = 0;
      queueHeroFrame();
    });

    window.addEventListener("scroll", function () {
      updateHeroDepth();
      queueHeroFrame();
    }, { passive: true });

    window.addEventListener("resize", function () {
      updateHeroDepth();
      queueHeroFrame();
    }, { passive: true });

    updateHeroDepth();
    queueHeroFrame();
  }

  document.querySelectorAll(".tilt-card").forEach(function (card) {
    if (reducedMotion) return;

    card.addEventListener("mousemove", function (event) {
      var rect = card.getBoundingClientRect();
      var x = ((event.clientX - rect.left) / rect.width - 0.5) * 10;
      var y = ((event.clientY - rect.top) / rect.height - 0.5) * -10;
      card.style.transform = "perspective(1000px) rotateY(" + x + "deg) rotateX(" + y + "deg) translateY(-6px)";
    });
    card.addEventListener("mouseleave", function () {
      card.style.transform = "";
    });
  });
}());

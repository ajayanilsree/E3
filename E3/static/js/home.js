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
    return;
  }

  var revealObserver = new IntersectionObserver(function (entries) {
    entries.forEach(function (entry) {
      if (!entry.isIntersecting) return;
      var delay = entry.target.getAttribute("data-delay") || 0;
      setTimeout(function () {
        entry.target.classList.add("in-view");
      }, delay);
      revealObserver.unobserve(entry.target);
    });
  }, { threshold: 0.14 });

  reveals.forEach(function (item) {
    revealObserver.observe(item);
  });

  if (reducedMotion) return;

  var heroVisual = document.querySelector(".lux-hero-visual");
  var sceneLayers = document.querySelectorAll(".scene-layer");
  if (heroVisual) {
    window.addEventListener("mousemove", function (event) {
      var x = (event.clientX / window.innerWidth - 0.5) * 5;
      var y = (event.clientY / window.innerHeight - 0.5) * -3.5;
      heroVisual.style.transform = "perspective(1400px) rotateY(" + x + "deg) rotateX(" + y + "deg)";
      sceneLayers.forEach(function (layer) {
        var depth = parseFloat(layer.getAttribute("data-depth") || "10");
        layer.style.marginLeft = (x * depth / 42) + "px";
        layer.style.marginTop = (-y * depth / 46) + "px";
      });
    }, { passive: true });
  }

  document.querySelectorAll(".tilt-card").forEach(function (card) {
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

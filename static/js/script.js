/* =========================================================
   TRUCK DESIGN POZANTI - script.js
   ========================================================= */

document.addEventListener("DOMContentLoaded", function () {

  /* ---------- MOBİL HAMBURGER MENÜ ---------- */
  var hamburger = document.getElementById("hamburgerBtn");
  var nav = document.getElementById("mainNav");
  if (hamburger && nav) {
    hamburger.addEventListener("click", function () {
      var isOpen = nav.classList.toggle("open");
      hamburger.classList.toggle("open", isOpen);
      hamburger.setAttribute("aria-expanded", isOpen ? "true" : "false");
    });
    nav.querySelectorAll("a").forEach(function (link) {
      link.addEventListener("click", function () {
        nav.classList.remove("open");
        hamburger.classList.remove("open");
      });
    });
  }

  /* ---------- HERO SLIDER (otomatik, sonsuz döngü) ---------- */
  var slider = document.getElementById("heroSlider");
  if (slider) {
    var slides = slider.querySelectorAll(".hero-slide");
    var dots = slider.querySelectorAll(".hero-dot");
    var current = 0;
    var intervalMs = 6000; // 6 saniye
    var timer = null;

    function showSlide(index) {
      slides.forEach(function (s, i) {
        s.classList.toggle("active", i === index);
      });
      dots.forEach(function (d, i) {
        d.classList.toggle("active", i === index);
      });
      current = index;
    }

    function nextSlide() {
      var next = (current + 1) % slides.length;
      showSlide(next);
    }

    function startAutoplay() {
      if (slides.length > 1) {
        timer = setInterval(nextSlide, intervalMs);
      }
    }

    function stopAutoplay() {
      if (timer) clearInterval(timer);
    }

    if (slides.length > 0) {
      dots.forEach(function (dot) {
        dot.addEventListener("click", function () {
          stopAutoplay();
          showSlide(parseInt(dot.dataset.index, 10));
          startAutoplay();
        });
      });
      startAutoplay();

      // Sekme arka plandayken gereksiz timer çalışmasını durdur
      document.addEventListener("visibilitychange", function () {
        if (document.hidden) {
          stopAutoplay();
        } else {
          startAutoplay();
        }
      });
    }
  }

  /* ---------- GALERİ LIGHTBOX ---------- */
  var galleryItems = document.querySelectorAll(".gallery-item");
  var lightbox = document.getElementById("lightbox");
  if (galleryItems.length > 0 && lightbox && typeof GALLERY_ITEMS !== "undefined") {
    var lbImg = document.getElementById("lightboxImg");
    var lbTitle = document.getElementById("lightboxTitle");
    var lbDesc = document.getElementById("lightboxDesc");
    var lbDate = document.getElementById("lightboxDate");
    var closeBtn = document.getElementById("lightboxClose");

    galleryItems.forEach(function (item) {
      item.addEventListener("click", function () {
        var idx = parseInt(item.dataset.index, 10);
        var data = GALLERY_ITEMS[idx];
        if (!data) return;
        lbImg.src = data.image || "";
        lbImg.alt = data.title || "";
        lbTitle.textContent = data.title || "";
        lbDesc.textContent = data.desc || "";
        lbDate.textContent = data.date || "";
        lightbox.classList.add("open");
      });
    });

    function closeLightbox() {
      lightbox.classList.remove("open");
      lbImg.src = "";
    }

    if (closeBtn) closeBtn.addEventListener("click", closeLightbox);
    lightbox.addEventListener("click", function (e) {
      if (e.target === lightbox) closeLightbox();
    });
    document.addEventListener("keydown", function (e) {
      if (e.key === "Escape") closeLightbox();
    });
  }

  /* ---------- FLASH MESAJLARI OTOMATİK GİZLEME ---------- */
  var flashes = document.querySelectorAll(".flash");
  if (flashes.length > 0) {
    setTimeout(function () {
      flashes.forEach(function (f) {
        f.style.transition = "opacity 0.5s ease";
        f.style.opacity = "0";
        setTimeout(function () { f.style.display = "none"; }, 500);
      });
    }, 6000);
  }

});

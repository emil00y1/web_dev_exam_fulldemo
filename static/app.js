// APP JS

function render_items(data) {
  data = JSON.parse(data);
  data.forEach((e) => {
    console.log(e);
    var marker = L.marker(e.coords).addTo(map);
    marker.bindPopup(e.popup);
  });
}
// Quantity control handlers
document.addEventListener("DOMContentLoaded", () => {
  // Handle decrease button clicks
  document.addEventListener("click", (e) => {
    const decreaseBtn = e.target.closest(".menu-quantity-decrease");
    if (decreaseBtn) {
      const itemId = decreaseBtn.dataset.itemId;
      updateQuantity(itemId, -1);
    }
  });
  // Handle increase button clicks
  document.addEventListener("click", (e) => {
    const increaseBtn = e.target.closest(".menu-quantity-increase");
    if (increaseBtn) {
      const itemId = increaseBtn.dataset.itemId;
      updateQuantity(itemId, 1);
    }
  });

  if (document.querySelector(".image-carousel")) {
    initializeCarousels();
  }

  if (document.querySelector("#view_signup")) {
    initializeSignupForm();
  }
   if (document.querySelector(".tab-container")) {
    initializeTabs();
  }
  showClearBtn();

});

function showClearBtn() {
    // Get all search inputs and clear buttons
    const searchInputs = document.querySelectorAll('.search-input');
    const clearButtons = document.querySelectorAll('.clear-button');
    
    // Loop through each search input to add event listeners
    searchInputs.forEach((input) => {
        // Find the associated clear button within the same search wrapper
        const clearButton = input.closest('.search-wrapper').querySelector('.clear-button');
        
        // Add input event listener to show/hide clear button
        input.addEventListener('input', function() {
            clearButton.classList.toggle('hidden', !this.value);
        });
        
        // Initialize clear button visibility based on initial input value
        clearButton.classList.toggle('hidden', !input.value);
    });

    // Add click event listeners to all clear buttons
    clearButtons.forEach((button) => {
        button.addEventListener('click', function() {
            // Find the closest search wrapper and get its input
            const wrapper = this.closest('.search-wrapper');
            const input = wrapper.querySelector('.search-input');
            
            // Clear the input value
            input.value = '';
            
            // Hide the clear button
            this.classList.add('hidden');
            
            // Focus the input
            input.focus();
        });
    });
}




// Signup form initialization and handling
function initializeSignupForm() {
  const roleSelect = document.getElementById("user_role");
  const addressFields = document.getElementById("address_fields");

  if (roleSelect && addressFields) {
    // Function to handle showing/hiding address fields
    function toggleAddressFields() {
      const selectedRole =
        roleSelect.options[roleSelect.selectedIndex].text.toLowerCase();
      if (selectedRole === "restaurant") {
        // Show address fields and make them required
        addressFields.classList.remove("d-none");
        ["street", "house_number", "postcode", "city"].forEach((field) => {
          const input = document.getElementById(field);
          if (input) {
            input.required = true;
            // Add validation classes for visual feedback
            input.classList.add("validate-input");
          }
        });
      } else {
        // Hide address fields and remove required attribute
        addressFields.classList.add("d-none");
        ["street", "house_number", "postcode", "city"].forEach((field) => {
          const input = document.getElementById(field);
          if (input) {
            input.required = false;
            input.classList.remove("validate-input");
          }
        });
      }
    }

    // Initial check on page load
    toggleAddressFields();

    // Listen for role changes
    roleSelect.addEventListener("change", toggleAddressFields);
  }
}

function updateQuantity(itemId, change) {
  const decreaseBtn = document.querySelector(
    `.menu-quantity-decrease[data-item-id="${itemId}"]`
  );
  const input = document.getElementById(`quantity_${itemId}`);
  const totalPriceSpan = document.getElementById(`total_price_${itemId}`);
  const button = totalPriceSpan.closest("button");
  const basePrice = parseFloat(button.dataset.basePrice);
  let value = parseInt(input.value) + change;
  if (value < 1) value = 1;
  input.value = value;
  if (value === 1) {
    decreaseBtn.classList.add("cursor-not-allowed");
  } else {
    decreaseBtn.classList.remove("cursor-not-allowed");
  }
  const total = basePrice * value;
  totalPriceSpan.textContent = "$" + total.toFixed(2);
}

// Burger Menu functionality
document.addEventListener("DOMContentLoaded", function () {
  const burgerBtn = document.getElementById("burger-menu-btn");
  const closeBtn = document.getElementById("close-menu-btn");
  const mobileMenu = document.getElementById("mobile-menu");

  if (burgerBtn && mobileMenu && closeBtn) {
    burgerBtn.addEventListener("click", function () {
      mobileMenu.classList.remove("translate-x-(100%)", "animation-slideOut");
      mobileMenu.classList.add("animation-slideIn");
      document.body.style.overflow = "hidden";
    });

    closeBtn.addEventListener("click", function () {
      mobileMenu.classList.remove("animation-slideIn");
      mobileMenu.classList.add("animation-slideOut");
      document.body.style.overflow = "";

      mobileMenu.addEventListener(
        "animationend",
        function () {
          mobileMenu.classList.add("translate-x-(100%)");
        },
        { once: true }
      );
    });
  }
});

function initializeCarousels() {
  const carousels = document.querySelectorAll(".image-carousel");

  carousels.forEach((carousel) => {
    const track = carousel.querySelector(".carousel-track");
    const prev = carousel.querySelector(".carousel-prev");
    const next = carousel.querySelector(".carousel-next");
    const dots = carousel.querySelectorAll(".pagination-dot");

    if (!track || !prev || !next) return;

    const images = track.querySelectorAll("img");
    const totalImages = images.length;
    if (totalImages <= 1) return;

    let currentIndex = 0;
    let isTransitioning = false;

    // Set initial track width and transition
    track.style.width = `${totalImages * 100}%`;
    track.style.transition = "transform 0.25s ease-out";

    // Set equal widths for all images
    images.forEach((img) => {
      img.style.width = `${100 / totalImages}%`;
    });

    function slide(direction) {
      if (isTransitioning) return;

      const newIndex =
        direction === "next"
          ? Math.min(currentIndex + 1, totalImages - 1)
          : Math.max(currentIndex - 1, 0);

      if (newIndex === currentIndex) return;

      isTransitioning = true;

      // Apply transform directly to element
      track.style.transform = `translateX(-${newIndex * (100 / totalImages)}%)`;

      // Update current index and reset transition lock after animation
      setTimeout(() => {
        currentIndex = newIndex;
        isTransitioning = false;

        // Update navigation visibility
        prev.style.visibility = currentIndex === 0 ? "hidden" : "visible";
        next.style.visibility =
          currentIndex === totalImages - 1 ? "hidden" : "visible";

        // Update dots
        dots.forEach((dot, index) => {
          dot.style.opacity = index === currentIndex ? "1" : "0.5";
        });
      }, 250);
    }

    // Event listeners
    prev.addEventListener("click", () => slide("prev"));
    next.addEventListener("click", () => slide("next"));

    // Initialize navigation visibility
    prev.style.visibility = "hidden";
    next.style.visibility = totalImages > 1 ? "visible" : "hidden";
  });
}

function initializeTabs() {
  const tabButtons = document.querySelectorAll(".tab-button");
  const tabContents = document.querySelectorAll(".tab-content");
  function switchTab(tabId) {
    // Update button styles
    tabButtons.forEach((btn) => {
      const btnSvg = btn.querySelector("svg")

      if (btn.dataset.tab === tabId) {
        btn.classList.add("active", "text-c-tealblue:-5");
        btn.classList.remove("text-c-gray:-5");
        btnSvg.classList.add("fill-c-tealblue:-5")
        btnSvg.classList.remove("fill-c-gray:-5")
      } else {
        btn.classList.remove("active", "text-c-tealblue:-5");
        btn.classList.add("text-c-gray:-5");
        btnSvg.classList.remove("fill-c-tealblue:-5")
        btnSvg.classList.add("fill-c-gray:-5")
      }
    });

    // Update content visibility with logging
    tabContents.forEach((content) => {
      if (content.id === tabId) {
        content.classList.remove("d-none");
      } else {
        content.classList.add("d-none");
      }
    });

    // If switching to discover tab, refresh map
    if (tabId === "discover" && window.restaurantMap) {
      setTimeout(() => {
        window.restaurantMap.refreshSize();
      }, 100);
    }

    localStorage.setItem("activeTab", tabId);
  }

  // Add click handlers to tab buttons
  tabButtons.forEach((button) => {
    button.addEventListener("click", () => {
      switchTab(button.dataset.tab);
    });
  });

  // Initialize with saved preference or default
  const savedTab = localStorage.getItem("activeTab") || "discover";
  switchTab(savedTab);
}

// MOJO CUSTOMIZATION
mojo({
  base: {
    breakpoints: {
      xs: {
        min: "375px", // The minimum width for this breakpoint
      },
      xxl: {
        fontSize: "16px",
      },
      xm: {
        min: "1124px",
      },
    },
    definedValues: {
      animation: {
        slideIn: {
          dur: "0.25s ease-out",
          keyframes: {
            "0%": {
              idle: "transform:translateX(100%)",
            },
            "100%": {
              idle: "transform:translateX(0)",
            },
          },
        },
        slideOut: {
          dur: "0.25s ease-out",
          keyframes: {
            "0%": {
              idle: "transform:translateX(0)",
            },
            "100%": {
              idle: "transform:translateX(100%)",
            },
          },
        },
        carouselNext: {
          dur: "0.25s ease-out",
          keyframes: {
            "0%": {
              idle: "transform:translateX(0)",
            },
            "100%": {
              idle: "transform:translateX(-100%)",
            },
          },
        },
        carouselPrev: {
          dur: "0.25s ease-out",
          keyframes: {
            "0%": {
              idle: "transform:translateX(-100%)",
            },
            "100%": {
              idle: "transform:translateX(0)",
            },
          },
        },
      },
    },
  },
});

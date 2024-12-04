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

  if (document.querySelector('.image-carousel')) {
    initializeCarousels();
  }
});

function updateQuantity(itemId, change) {
  const decreaseBtn = document.querySelector(
    `.menu-quantity-decrease[data-item-id="${itemId}"]`
  );
  const input = document.getElementById(`quantity_${itemId}`);
  const totalPriceSpan = document.getElementById(`total_price_${itemId}`);
  const button = totalPriceSpan.closest('button');
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
  totalPriceSpan.textContent = total.toFixed(2);
}


// Burger Menu functionality
document.addEventListener('DOMContentLoaded', function() {
    const burgerBtn = document.getElementById('burger-menu-btn');
    const closeBtn = document.getElementById('close-menu-btn');
    const mobileMenu = document.getElementById('mobile-menu');
   
    if (burgerBtn && mobileMenu && closeBtn) {
        burgerBtn.addEventListener('click', function() {
            mobileMenu.classList.remove('translate-x-(100%)', 'animation-slideOut');
            mobileMenu.classList.add('animation-slideIn');
            document.body.style.overflow = 'hidden';
        });

        closeBtn.addEventListener('click', function() {
            mobileMenu.classList.remove('animation-slideIn');
            mobileMenu.classList.add('animation-slideOut');
            document.body.style.overflow = '';
            
            mobileMenu.addEventListener('animationend', function() {
                mobileMenu.classList.add('translate-x-(100%)');
            }, { once: true });
        });
    }
});


function initializeCarousels() {
  const carousels = document.querySelectorAll('.image-carousel');
  
  carousels.forEach(carousel => {
    const track = carousel.querySelector('.carousel-track');
    const prev = carousel.querySelector('.carousel-prev');
    const next = carousel.querySelector('.carousel-next');
    const dots = carousel.querySelectorAll('.pagination-dot');
    
    if (!track || !prev || !next) return;
    
    const images = track.querySelectorAll('img');
    const totalImages = images.length;
    if (totalImages <= 1) return;
    
    let currentIndex = 0;
    let isTransitioning = false;

    // Set initial track width and transition
    track.style.width = `${totalImages * 100}%`;
    track.style.transition = 'transform 0.25s ease-out';
    
    // Set equal widths for all images
    images.forEach(img => {
      img.style.width = `${100 / totalImages}%`;
    });

    function slide(direction) {
      if (isTransitioning) return;
      
      const newIndex = direction === 'next' 
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
        prev.style.visibility = currentIndex === 0 ? 'hidden' : 'visible';
        next.style.visibility = currentIndex === totalImages - 1 ? 'hidden' : 'visible';
        
        // Update dots
        dots.forEach((dot, index) => {
          dot.style.opacity = index === currentIndex ? '1' : '0.5';
        });
      }, 250);
    }
    
    // Event listeners
    prev.addEventListener('click', () => slide('prev'));
    next.addEventListener('click', () => slide('next'));
    
    // Initialize navigation visibility
    prev.style.visibility = 'hidden';
    next.style.visibility = totalImages > 1 ? 'visible' : 'hidden';
  });
}

// MOJO CUSTOMIZATION
mojo({
    base: {
        breakpoints: {
          "min-390px": {
            min: "390px", // The minimum width for this breakpoint
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
                }
            }
        },
    },
});
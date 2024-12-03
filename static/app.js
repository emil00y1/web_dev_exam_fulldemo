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

// MOJO CUSTOMIZATION
mojo({
    base: {
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
                }
            }
        },
    },
});
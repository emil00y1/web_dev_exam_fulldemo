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
    const decreaseBtn = e.target.closest(".quantity-btn-decrease");
    if (decreaseBtn) {
      const itemId = decreaseBtn.dataset.itemId;
      updateQuantity(itemId, -1);
    }
  });

  // Handle increase button clicks
  document.addEventListener("click", (e) => {
    const increaseBtn = e.target.closest(".quantity-btn-increase");
    if (increaseBtn) {
      const itemId = increaseBtn.dataset.itemId;
      updateQuantity(itemId, 1);
    }
  });
});

function updateQuantity(itemId, change) {
  const decreaseBtn = document.querySelector(
    `.quantity-btn-decrease[data-item-id="${itemId}"]`
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

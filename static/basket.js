document.addEventListener('DOMContentLoaded', () => {
    const basketButton = document.getElementById('basket-button');
    const basketDropdown = document.getElementById('basket-dropdown');
    let lastUpdate = 0;
    const MIN_UPDATE_DELAY = 200; // Minimum milliseconds between updates
   
    // Close dropdown when clicking outside
    document.addEventListener('click', (e) => {
        if (!basketButton.contains(e.target) && !basketDropdown.contains(e.target)) {
            basketDropdown.classList.add('hidden');
        }
    });

    // Toggle dropdown
    basketButton.addEventListener('click', () => {
        basketDropdown.classList.toggle('hidden');
    });

    // Handle decrease button clicks
    document.addEventListener('click', (e) => {
        const decreaseBtn = e.target.closest('.basket-quantity-decrease');
        if (decreaseBtn && canUpdate()) {
            const itemId = decreaseBtn.dataset.itemId;
            const currentQuantity = parseInt(document.getElementById(`basket_quantity_${itemId}`).textContent);
            
            if (currentQuantity > 1) {
                updateBasketUI(itemId, -1);
                const form = document.getElementById(`frm_decrease_${itemId}`);
                const button = form.querySelector('button[mix-post]');
                if (button) {
                    button.click();
                    lastUpdate = Date.now();
                }
            }
        }
    });

    // Handle increase button clicks
    document.addEventListener('click', (e) => {
        const increaseBtn = e.target.closest('.basket-quantity-increase');
        if (increaseBtn && canUpdate()) {
            const itemId = increaseBtn.dataset.itemId;
            updateBasketUI(itemId, 1);
            const form = document.getElementById(`frm_increase_${itemId}`);
            const button = form.querySelector('button[mix-post]');
            if (button) {
                button.click();
                lastUpdate = Date.now();
            }
        }
    });

    function canUpdate() {
        return Date.now() - lastUpdate >= MIN_UPDATE_DELAY;
    }
});

// Rest of your existing updateBasketUI and updateBasketTotal functions remain the same

function updateBasketUI(itemId, change) {
    // Get elements
    const quantityElement = document.getElementById(`basket_quantity_${itemId}`);
    const itemTotalElement = document.getElementById(`basket_item_total_${itemId}`);
    const decreaseBtn = document.querySelector(`.basket-quantity-decrease[data-item-id="${itemId}"]`);
    const increaseBtn = document.querySelector(`.basket-quantity-increase[data-item-id="${itemId}"]`);
    
    // Get current values
    const currentQuantity = parseInt(quantityElement.textContent);
    const itemPrice = parseFloat(decreaseBtn.dataset.itemPrice);
    
    // Calculate new quantity
    const newQuantity = Math.max(1, currentQuantity + change);
    
    // Update quantity display
    quantityElement.textContent = newQuantity;
    
    // Update item total
    const newItemTotal = (newQuantity * itemPrice).toFixed(2);
    itemTotalElement.textContent = newItemTotal;
    
    // Update decrease button state
    if (newQuantity <= 1) {
        decreaseBtn.classList.add('cursor-not-allowed');
        decreaseBtn.disabled = true;
    } else {
        decreaseBtn.classList.remove('cursor-not-allowed');
        decreaseBtn.disabled = false;
    }
    
    // Update basket total
    updateBasketTotal();
}

function updateBasketTotal() {
    const itemTotals = document.querySelectorAll('[id^="basket_item_total_"]');
    let total = 0;
    
    itemTotals.forEach(element => {
        total += parseFloat(element.textContent);
    });
    
    document.getElementById('basket_total').textContent = total.toFixed(2);
}
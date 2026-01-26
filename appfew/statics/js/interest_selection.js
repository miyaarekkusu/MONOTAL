function toggleSelection(element) {
    const container = element.querySelector('div');
    const checkmark = container.querySelector('div:last-child');
    const img = container.querySelector('img');

    // Current State Check (by checking ring class)
    const isSelected = container.classList.contains('ring-4');

    if (isSelected) {
        // Deselect
        container.classList.remove('ring-4', 'ring-pink-600', 'shadow-sm');
        container.classList.add('ring-0', 'ring-transparent', 'hover:ring-2', 'hover:ring-zinc-200');
        checkmark.classList.remove('scale-100');
        checkmark.classList.add('scale-0');
        if (img) img.classList.remove('opacity-90');
    } else {
        // Select
        container.classList.remove('ring-0', 'ring-transparent', 'hover:ring-2', 'hover:ring-zinc-200');
        container.classList.add('ring-4', 'ring-pink-600', 'shadow-sm');
        checkmark.classList.remove('scale-0');
        checkmark.classList.add('scale-100');
        if (img) img.classList.add('opacity-90');
    }

    // Update Count
    updateCount();
}

function updateCount() {
    const countEl = document.getElementById('selected-count');
    const count = document.querySelectorAll('#interestGrid .ring-pink-600').length;
    countEl.innerText = count;
}

document.addEventListener('DOMContentLoaded', function () {
    // Initialize count on page load
    updateCount();

    // Submit button handler
    document.getElementById('submitBtn').addEventListener('click', function () {
        const form = document.getElementById('interestForm');
        const hiddenInputs = document.getElementById('hiddenInputs');

        // Clear existing hidden inputs
        hiddenInputs.innerHTML = '';

        // Collect selected category IDs
        const selectedCards = document.querySelectorAll('#interestGrid [data-category-id]');
        selectedCards.forEach(function (card) {
            const container = card.querySelector('div');
            if (container.classList.contains('ring-4')) {
                const input = document.createElement('input');
                input.type = 'hidden';
                input.name = 'category_ids';
                input.value = card.getAttribute('data-category-id');
                hiddenInputs.appendChild(input);
            }
        });

        form.submit();
    });
});

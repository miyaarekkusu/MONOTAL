function toggleSelection(element) {
    const container = element.querySelector('div');
    const checkmark = container.querySelector('div:last-child');
    const img = container.querySelector('img');

    // Current State Check (by checking ring class)
    const isSelected = container.classList.contains('ring-4');

    if (isSelected) {
        // Deselect
        container.classList.remove('ring-4', 'ring-pink-600');
        container.classList.add('ring-0', 'ring-transparent', 'hover:ring-2', 'hover:ring-zinc-200');
        checkmark.classList.remove('scale-100');
        checkmark.classList.add('scale-0');
        img.classList.remove('opacity-90');
    } else {
        // Select
        container.classList.remove('ring-0', 'ring-transparent', 'hover:ring-2', 'hover:ring-zinc-200');
        container.classList.add('ring-4', 'ring-pink-600');
        checkmark.classList.remove('scale-0');
        checkmark.classList.add('scale-100');
        img.classList.add('opacity-90');
    }

    // Update Count
    const countEl = document.getElementById('selected-count');
    let count = document.querySelectorAll('.ring-pink-600').length;
    countEl.innerText = count;
}

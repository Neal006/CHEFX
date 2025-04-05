document.addEventListener('DOMContentLoaded', () => {
    const form = document.getElementById('converterForm');
    const resultContainer = document.getElementById('resultContainer');
    const errorContainer = document.getElementById('errorContainer');
    const loadingContainer = document.querySelector('.loading-container');
    const inputs = form.querySelectorAll('input');

    // Add input animations and validation
    inputs.forEach(input => {
        const wrapper = input.parentElement;
        const icon = wrapper.querySelector('.input-icon');

        input.addEventListener('focus', () => {
            wrapper.classList.add('focused');
            if (icon) icon.style.transform = 'translateY(-50%) scale(1.1)';
        });

        input.addEventListener('blur', () => {
            wrapper.classList.remove('focused');
            if (icon) icon.style.transform = 'translateY(-50%) scale(1)';
            validateInput(input);
        });

        input.addEventListener('input', () => {
            validateInput(input);
        });
    });

    function validateInput(input) {
        const wrapper = input.parentElement;
        if (input.value.trim()) {
            wrapper.classList.add('valid');
            wrapper.classList.remove('invalid');
        } else {
            wrapper.classList.remove('valid');
            wrapper.classList.add('invalid');
        }
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const measurement = document.getElementById('measurement').value.trim();
        const ingredient = document.getElementById('ingredient').value.trim();
        
        if (!measurement || !ingredient) {
            showError('Please fill in both measurement and ingredient fields');
            return;
        }

        // Hide any previous results or errors with animation
        if (resultContainer.style.display !== 'none') {
            resultContainer.style.opacity = '0';
            resultContainer.style.transform = 'translateY(10px)';
            setTimeout(() => {
                resultContainer.style.display = 'none';
            }, 300);
        }

        if (errorContainer.style.display !== 'none') {
            errorContainer.style.opacity = '0';
            setTimeout(() => {
                errorContainer.style.display = 'none';
            }, 300);
        }
        
        // Show loading spinner with animation
        loadingContainer.style.display = 'flex';
        loadingContainer.style.opacity = '0';
        setTimeout(() => {
            loadingContainer.style.opacity = '1';
        }, 10);

        try {
            const response = await fetch('/api/convert', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ measurement, ingredient })
            });

            const data = await response.json();

            if (response.ok) {
                displayResults(data);
            } else {
                showError(data.error || 'Failed to convert measurement');
            }
        } catch (error) {
            showError('An error occurred while converting the measurement');
            console.error('Conversion error:', error);
        } finally {
            // Hide loading spinner with animation
            loadingContainer.style.opacity = '0';
            setTimeout(() => {
                loadingContainer.style.display = 'none';
            }, 300);
        }
    });

    function displayResults(data) {
        const resultContainer = document.getElementById('resultContainer');
        
        // Update all result fields
        document.getElementById('interpretation').textContent = data.interpretation || 'N/A';
        document.getElementById('grams').textContent = data.grams || 'N/A';
        document.getElementById('ounces').textContent = data.ounces || 'N/A';
        document.getElementById('milliliters').textContent = data.milliliters || 'N/A';
        document.getElementById('cups').textContent = data.cups || 'N/A';
        document.getElementById('tablespoons').textContent = data.tablespoons || 'N/A';
        document.getElementById('teaspoons').textContent = data.teaspoons || 'N/A';
        
        if (data.ingredient_info) {
            document.getElementById('category').textContent = data.ingredient_info.category || 'N/A';
            document.getElementById('state').textContent = data.ingredient_info.state || 'N/A';
            document.getElementById('density').textContent = data.ingredient_info.density || 'N/A';
        }

        // Show results with staggered animation
        resultContainer.style.display = 'block';
        resultContainer.style.opacity = '0';
        resultContainer.style.transform = 'translateY(20px)';

        // Trigger reflow
        resultContainer.offsetHeight;

        // Add animations
        resultContainer.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
        resultContainer.style.opacity = '1';
        resultContainer.style.transform = 'translateY(0)';

        // Animate result cards with stagger
        const cards = resultContainer.querySelectorAll('.result-card');
        cards.forEach((card, index) => {
            card.style.opacity = '0';
            card.style.transform = 'translateY(20px)';
            setTimeout(() => {
                card.style.transition = 'opacity 0.5s ease-out, transform 0.5s ease-out';
                card.style.opacity = '1';
                card.style.transform = 'translateY(0)';
            }, 100 * (index + 1));
        });

        // Scroll to results
        setTimeout(() => {
            resultContainer.scrollIntoView({ 
                behavior: 'smooth', 
                block: 'nearest'
            });
        }, 100);
    }

    function showError(message) {
        const errorContainer = document.getElementById('errorContainer');
        errorContainer.querySelector('p').textContent = message;
        
        // Show error with animation
        errorContainer.style.display = 'flex';
        errorContainer.style.opacity = '0';
        errorContainer.style.transform = 'translateX(-10px)';

        // Trigger reflow
        errorContainer.offsetHeight;

        // Add animation
        errorContainer.style.transition = 'opacity 0.3s ease-out, transform 0.3s ease-out';
        errorContainer.style.opacity = '1';
        errorContainer.style.transform = 'translateX(0)';
        
        // Scroll to error
        errorContainer.scrollIntoView({ 
            behavior: 'smooth', 
            block: 'nearest'
        });
    }

    // Add hover effects for result cards
    const resultCards = document.querySelectorAll('.result-card');
    resultCards.forEach(card => {
        card.addEventListener('mouseenter', () => {
            card.style.transform = 'translateY(-4px)';
            card.style.boxShadow = '0 12px 24px rgba(0, 0, 0, 0.12)';
        });

        card.addEventListener('mouseleave', () => {
            card.style.transform = 'translateY(0)';
            card.style.boxShadow = '0 8px 16px rgba(0, 0, 0, 0.08)';
        });
    });
});

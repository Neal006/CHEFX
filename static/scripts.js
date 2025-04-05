// DOM Elements
const hamburger = document.querySelector('.hamburger');
const navLinks = document.querySelector('.nav-links');
const header = document.querySelector('.navbar');
const mainContent = document.querySelector('.dashboard-container');

// Prevent FOUC (Flash of Unstyled Content)
document.documentElement.style.visibility = 'hidden';
document.addEventListener('DOMContentLoaded', function() {
    document.documentElement.style.visibility = 'visible';
});

// Mobile Menu Toggle
hamburger?.addEventListener('click', () => {
    navLinks?.classList.toggle('active');
});

// Close mobile menu when clicking outside
document.addEventListener('click', (e) => {
    if (!e.target.closest('.navbar') && navLinks?.classList.contains('active')) {
        navLinks.classList.remove('active');
    }
});

// Smooth Scroll for Anchor Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth'
            });
            navLinks?.classList.remove('active');
        }
    });
});

// Optimize Intersection Observer
const observerOptions = {
    rootMargin: '50px 0px',
    threshold: 0.1
};

// Single Observer for all animations
const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('visible');
            if (entry.target.classList.contains('animate-fade-in')) {
                observer.unobserve(entry.target); // Stop observing after animation
            }
        }
    });
}, observerOptions);

// Observe elements only after DOM is fully loaded
document.addEventListener('DOMContentLoaded', () => {
    // Animate elements
    document.querySelectorAll('.animate-fade-in, .feature-card, .pricing-card, .contact-card').forEach(element => {
        observer.observe(element);
    });
    
    // Set fixed dimensions for images before loading
    document.querySelectorAll('img').forEach(img => {
        if (img.getAttribute('width') && img.getAttribute('height')) {
            img.style.aspectRatio = `${img.getAttribute('width')} / ${img.getAttribute('height')}`;
        }
    });
});

// Optimize form handling
const forms = document.querySelectorAll('form');
forms.forEach(form => {
    form.addEventListener('submit', (e) => {
        e.preventDefault();
        const emailInput = form.querySelector('input[type="email"]');
        if (emailInput && isValidEmail(emailInput.value)) {
            if (form.classList.contains('newsletter-form')) {
                handleNewsletterSubmit(emailInput.value);
            }
        } else if (emailInput) {
            showError(emailInput, 'Please enter a valid email address');
        }
    });
});

function isValidEmail(email) {
    return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email);
}

function showError(input, message) {
    const existingError = input.parentElement.querySelector('.error-message');
    if (existingError) {
        existingError.remove();
    }
    
    const errorDiv = document.createElement('div');
    errorDiv.className = 'error-message';
    errorDiv.textContent = message;
    errorDiv.style.cssText = 'color: var(--error-color); font-size: 0.875rem; margin-top: 0.25rem;';
    
    input.parentElement.appendChild(errorDiv);
    setTimeout(() => errorDiv.remove(), 3000);
}

function handleNewsletterSubmit(email) {
    const form = document.querySelector('.newsletter-form');
    const submitButton = form?.querySelector('button[type="submit"]');
    
    if (!submitButton) return;
    
    const originalText = submitButton.textContent;
    submitButton.textContent = 'Subscribing...';
    submitButton.disabled = true;
    
    setTimeout(() => {
        submitButton.textContent = 'Subscribed!';
        submitButton.style.backgroundColor = 'var(--success-color)';
        form.reset();
        
        setTimeout(() => {
            submitButton.textContent = originalText;
            submitButton.style.backgroundColor = '';
            submitButton.disabled = false;
        }, 2000);
    }, 1000);
}

// Prevent layout shifts from images
document.addEventListener('DOMContentLoaded', function() {
    const images = document.querySelectorAll('img[src]');
    
    images.forEach(img => {
        // Set a default aspect ratio if not specified
        if (!img.style.aspectRatio) {
            img.style.aspectRatio = '16/9';
        }
        
        // Add loading="lazy" for images below the fold
        if (!img.hasAttribute('loading') && !img.closest('header, .hero')) {
            img.loading = 'lazy';
        }
        
        // Handle image load errors
        img.addEventListener('error', function() {
            this.style.display = 'none';
        });
    });
});

// Handle loading overlay
const loadingOverlay = document.querySelector('.loading-overlay');
if (loadingOverlay && mainContent) {
    // Show content immediately if already loaded
    if (document.readyState === 'complete') {
        loadingOverlay.style.display = 'none';
        mainContent.style.opacity = '1';
    } else {
        // Wait for everything to load
        window.addEventListener('load', () => {
            loadingOverlay.style.display = 'none';
            mainContent.style.opacity = '1';
        });
    }
}

// Header Scroll Effect
let lastScroll = 0;
window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll <= 0) {
        header?.classList.remove('scroll-up');
        return;
    }
    
    if (currentScroll > lastScroll && !header?.classList.contains('scroll-down')) {
        // Scrolling down
        header?.classList.remove('scroll-up');
        header?.classList.add('scroll-down');
    } else if (currentScroll < lastScroll && header?.classList.contains('scroll-down')) {
        // Scrolling up
        header?.classList.remove('scroll-down');
        header?.classList.add('scroll-up');
    }
    lastScroll = currentScroll;
});

// Newsletter Form
const newsletterForm = document.querySelector('.newsletter-form');
if (newsletterForm) {
    newsletterForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const email = newsletterForm.querySelector('input[type="email"]').value;
        
        try {
            // Add your newsletter subscription logic here
            console.log('Newsletter subscription for:', email);
            
            // Show success message
            const button = newsletterForm.querySelector('button');
            const originalText = button.textContent;
            button.textContent = 'Subscribed!';
            button.classList.add('success');
            
            // Reset after 2 seconds
            setTimeout(() => {
                button.textContent = originalText;
                button.classList.remove('success');
                newsletterForm.reset();
            }, 2000);
            
        } catch (error) {
            console.error('Newsletter subscription error:', error);
        }
    });
}

// Add CSS class when elements come into view
const revealOnScroll = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.classList.add('revealed');
        }
    });
}, {
    threshold: 0.1,
    rootMargin: '0px'
});

document.querySelectorAll('.feature-card, .pricing-card, .contact-card').forEach((el) => {
    revealOnScroll.observe(el);
});

/* Image Lazy Loading */
document.addEventListener('DOMContentLoaded', function() {
    // Add placeholder and lazy class to all images that have a src attribute
    const images = document.querySelectorAll('img[src]:not([loading="eager"])');
    images.forEach(img => {
        if (!img.complete && !img.dataset.loaded) {
            img.classList.add('lazy');
            if (img.parentNode) {  // Add null check for parent node
                addPlaceholder(img);
            }
        }
    });

    // Set up Intersection Observer for lazy loading
    if ('IntersectionObserver' in window) {
        const imageObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach(entry => {
                if (entry.isIntersecting) {
                    const img = entry.target;
                    if (img && !img.dataset.loaded) {  // Add null check and loaded check
                        loadImage(img);
                        observer.unobserve(img);
                    }
                }
            });
        }, {
            rootMargin: '50px 0px',
            threshold: 0.01
        });

        // Observe all images
        images.forEach(img => {
            if (img && !img.dataset.loaded) {  // Add null check and loaded check
                imageObserver.observe(img);
            }
        });
    } else {
        // Fallback for browsers that don't support IntersectionObserver
        images.forEach(img => {
            if (img && !img.dataset.loaded) {  // Add null check and loaded check
                loadImage(img);
            }
        });
    }
});

function addPlaceholder(img) {
    if (!img || !img.parentNode) return;  // Add guard clause
    
    // Remove existing placeholder if any
    const existingPlaceholder = img.previousSibling;
    if (existingPlaceholder?.classList?.contains('image-placeholder')) {
        existingPlaceholder.remove();
    }

    const placeholder = document.createElement('div');
    placeholder.className = 'image-placeholder';
    
    // Use natural dimensions if available, otherwise use element dimensions
    const width = img.naturalWidth || img.width || 100;
    const height = img.naturalHeight || img.height || 100;
    
    placeholder.style.width = `${width}px`;
    placeholder.style.height = `${height}px`;
    
    img.parentNode.insertBefore(placeholder, img);
}

function loadImage(img) {
    if (!img || img.dataset.loaded) return;  // Add guard clause
    
    const tempImage = new Image();
    tempImage.onload = () => {
        img.src = tempImage.src;
        img.classList.remove('lazy');
        img.classList.add('loaded');
        img.dataset.loaded = 'true';
        
        const placeholder = img.previousSibling;
        if (placeholder?.classList?.contains('image-placeholder')) {
            placeholder.remove();
        }
    };
    tempImage.src = img.src;
}

// Handle dynamic image loading (for content added after initial load)
const mutationObserver = new MutationObserver(mutations => {
    mutations.forEach(mutation => {
        mutation.addedNodes.forEach(node => {
            if (node.nodeType === 1 && node.tagName === 'IMG' && !node.dataset.loaded) {
                if (!node.complete) {
                    node.classList.add('lazy');
                    if (node.parentNode) {  // Add null check for parent node
                        addPlaceholder(node);
                    }
                }
            }
        });
    });
});

mutationObserver.observe(document.body, {
    childList: true,
    subtree: true
});



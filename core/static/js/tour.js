// Super simplified tour for DesiQ
document.addEventListener('DOMContentLoaded', function() {
    console.log('Tour.js loaded');
    
    // First add IDs to all navigation items for better targeting
    function addNavIDs() {
        console.log('Adding IDs to navigation items');
        // Main navigation
        const mainNavItems = document.querySelectorAll('.main-nav li a');
        mainNavItems.forEach((item, index) => {
            item.id = `nav-item-${index+1}`;
        });
        
        // User navigation
        const userNavItems = document.querySelectorAll('.user-nav li a');
        userNavItems.forEach((item, index) => {
            item.id = `user-nav-item-${index+1}`;
        });
    }
    
    // On page load, check if the tour is already completed and add class to body
    function checkTourCompleted() {
        const tourCompleted = localStorage.getItem('desiq_tour_completed') === 'true';
        if (tourCompleted) {
            console.log('Tour already completed, adding tour-completed class to body');
            document.body.classList.add('tour-completed');
        }
    }
    
    // Create a simple welcome popup
    function createSimpleTour() {
        console.log('Creating welcome tour popup');
        
        // Add IDs to navigation elements first
        addNavIDs();
        
        // Create container
        const tourContainer = document.createElement('div');
        tourContainer.id = 'simple-tour';
        tourContainer.style.position = 'fixed';
        tourContainer.style.top = '0';
        tourContainer.style.left = '0';
        tourContainer.style.width = '100%';
        tourContainer.style.height = '100%';
        tourContainer.style.backgroundColor = 'rgba(0, 0, 0, 0.7)';
        tourContainer.style.zIndex = '10000';
        tourContainer.style.display = 'flex';
        tourContainer.style.justifyContent = 'center';
        tourContainer.style.alignItems = 'center';
        
        // Create welcome box
        const welcomeBox = document.createElement('div');
        welcomeBox.style.width = '90%';
        welcomeBox.style.maxWidth = '500px';
        welcomeBox.style.padding = '30px';
        welcomeBox.style.borderRadius = '15px';
        welcomeBox.style.backgroundColor = 'white';
        welcomeBox.style.boxShadow = '0 5px 20px rgba(0, 0, 0, 0.2)';
        welcomeBox.style.textAlign = 'center';
        
        // Box content
        welcomeBox.innerHTML = `
            <h2 style="color: #1b309a; margin-top: 0; margin-bottom: 20px; font-size: 24px;">Welcome to DesiQ!</h2>
            <p style="color: #555; margin-bottom: 25px; line-height: 1.6;">
                Your personal decision intelligence platform. DesiQ helps you make better decisions
                through AI-powered mentors, decision scenarios, and personalized insights.
            </p>
            <div style="display: flex; justify-content: center; gap: 15px;">
                <button id="start-tour-btn" style="background-color: #1b309a; color: white; border: none; border-radius: 30px; padding: 12px 25px; font-size: 16px; cursor: pointer;">Start Tour</button>
                <button id="skip-tour-btn" style="background-color: transparent; color: #555; border: 1px solid #d1d5db; border-radius: 30px; padding: 12px 25px; font-size: 16px; cursor: pointer;">Skip Tour</button>
            </div>
        `;
        
        // Add to DOM
        tourContainer.appendChild(welcomeBox);
        document.body.appendChild(tourContainer);
        
        // Add event listeners using a small delay to ensure DOM is fully updated
        setTimeout(() => {
            const startBtn = document.getElementById('start-tour-btn');
            const skipBtn = document.getElementById('skip-tour-btn');
            
            console.log('Start button found:', !!startBtn);
            console.log('Skip button found:', !!skipBtn);
            
            if (startBtn) {
                startBtn.addEventListener('click', function(e) {
                    console.log('Start tour button clicked');
                    tourContainer.remove();
                    startTourSteps();
                });
            }
            
            if (skipBtn) {
                skipBtn.addEventListener('click', function(e) {
                    console.log('Skip tour button clicked');
                    tourContainer.remove();
                    // Mark tour as completed when skipped
                    localStorage.setItem('desiq_tour_completed', 'true');
                    // Add tour-completed class to body
                    document.body.classList.add('tour-completed');
                    // Hide tour button if it's visible
                    hideTourButton();
                });
            }
        }, 100);
    }
    
    // Simple tour with fixed overlay - this is the actual tour function
    function startTourSteps() {
        console.log('Starting tour steps...');
        
        // Make sure IDs are added
        addNavIDs();
        
        // Set up tour steps with element targets to highlight
        const steps = [
            // Dashboard Overview
            {
                title: 'Dashboard Overview',
                text: 'Your dashboard provides a complete overview of your decision-making journey. This is where you can access all platform features and track your progress.',
                position: 'center',
                target: '.frame, .content'
            },
            {
                title: 'Dashboard Header',
                text: 'This header shows your current section and contains important action buttons.',
                position: 'bottom',
                target: '.page-header, .dashboard-header'
            },
            
            // Sidebar Navigation
            {
                title: 'Main Navigation',
                text: 'The sidebar on the left provides quick access to all platform features. Let\'s explore each section.',
                position: 'right',
                target: '.sidebar, aside.sidebar'
            },
            {
                title: 'Dashboard',
                text: 'Return to this home screen to see your overview and recent activities.',
                position: 'left',
                target: '#nav-item-1, .main-nav li:nth-child(1) a'
            },
            {
                title: 'Know Yourself',
                text: 'Take personality tests to understand your decision-making style. This helps identify your strengths and areas for improvement.',
                position: 'left',
                target: '#nav-item-2, .main-nav li:nth-child(2) a'
            },
            {
                title: 'Decision Scenarios',
                text: 'Practice making decisions in realistic scenarios. These challenges build your skills in a safe environment before facing real-world decisions.',
                position: 'left',
                target: '#nav-item-3, .main-nav li:nth-child(3) a'
            },
            {
                title: 'Smart Mentors',
                text: 'Get personalized advice from AI-powered mentors specialized in different areas like career, relationships, finances, and more.',
                position: 'left',
                target: '#nav-item-4, .main-nav li:nth-child(4) a'
            },
            {
                title: 'Progress Tracking',
                text: 'Monitor your improvement over time with detailed analytics showing how your decision-making abilities have evolved.',
                position: 'left',
                target: '#nav-item-5, .main-nav li:nth-child(5) a'
            },
            {
                title: 'Community',
                text: 'Connect with other users, share experiences, and discuss challenging decisions in a supportive environment.',
                position: 'left',
                target: '#nav-item-6, .main-nav li:nth-child(6) a'
            },
            {
                title: 'Support',
                text: 'Get help with any platform features or report issues to our support team.',
                position: 'left',
                target: '#nav-item-7, .main-nav li:nth-child(7) a'
            },
            {
                title: 'Chat',
                text: 'Access your conversations with mentors and other users in one convenient place.',
                position: 'left',
                target: '#nav-item-8, .main-nav li:nth-child(8) a'
            },
            
            // User Options
            {
                title: 'User Options',
                text: 'Manage your profile, settings, and account from these options.',
                position: 'left',
                target: '.user-nav'
            },
            {
                title: 'Your Journey Begins',
                text: 'You\'re all set to start improving your decision-making skills with DesiQ! We recommend starting with the Know Yourself section to understand your decision style.',
                position: 'center',
                target: ''
            }
        ];
        
        // Current step
        let currentStep = 0;
        
        // Create tour overlay
        const overlay = document.createElement('div');
        overlay.style.position = 'fixed';
        overlay.style.top = '0';
        overlay.style.left = '0';
        overlay.style.width = '100%';
        overlay.style.height = '100%';
        overlay.style.backgroundColor = 'rgba(0, 0, 0, 0.5)';
        overlay.style.zIndex = '9999';
        
        // Create tour box
        const tourBox = document.createElement('div');
        tourBox.id = 'tour-box';
        tourBox.style.position = 'fixed';
        tourBox.style.width = '350px';
        tourBox.style.padding = '20px';
        tourBox.style.backgroundColor = 'white';
        tourBox.style.borderRadius = '10px';
        tourBox.style.boxShadow = '0 4px 12px rgba(0, 0, 0, 0.1)';
        tourBox.style.zIndex = '10000';
        
        // Create highlight element
        const highlight = document.createElement('div');
        highlight.id = 'tour-highlight';
        highlight.style.position = 'absolute';
        highlight.style.border = '3px solid #7669b2';
        highlight.style.borderRadius = '4px';
        highlight.style.boxShadow = '0 0 0 2000px rgba(0, 0, 0, 0.4)';
        highlight.style.zIndex = '9998';
        highlight.style.transition = 'all 0.3s ease-in-out';
        highlight.style.pointerEvents = 'none'; // Allow clicking through
        
        // Add to DOM first
        document.body.appendChild(overlay);
        document.body.appendChild(highlight);
        document.body.appendChild(tourBox);
        
        // Set initial position and update content
        updateTourStep(currentStep);
        
        // Navigation functions
        function nextStep() {
            console.log('Next step clicked');
            if (currentStep < steps.length - 1) {
                currentStep++;
                updateTourStep(currentStep);
            } else {
                // End tour
                console.log('Tour completed');
                endTour();
            }
        }
        
        function prevStep() {
            console.log('Previous step clicked');
            if (currentStep > 0) {
                currentStep--;
                updateTourStep(currentStep);
            }
        }
        
        function closeTour() {
            console.log('Tour closed');
            endTour();
        }
        
        function endTour() {
            // Remove all tour elements
            overlay.remove();
            tourBox.remove();
            highlight.remove();
            
            // Remove any existing highlights from elements
            document.querySelectorAll('.tour-highlighted-element').forEach(el => {
                el.classList.remove('tour-highlighted-element');
                el.style.zIndex = '';
                el.style.position = '';
                el.style.outline = '';
                el.style.backgroundColor = '';
            });
            
            // Store in localStorage that user has completed the tour
            localStorage.setItem('desiq_tour_completed', 'true');
            
            // Add tour-completed class to body
            document.body.classList.add('tour-completed');
            
            // Hide the tour button since tour is completed
            hideTourButton();
        }
        
        // Position the tour box
        function positionTourBox(box, position, targetElement) {
            if (!targetElement || position === 'center') {
                box.style.top = '50%';
                box.style.left = '50%';
                box.style.transform = 'translate(-50%, -50%)';
                return;
            }
            
            const rect = targetElement.getBoundingClientRect();
            const boxRect = box.getBoundingClientRect();
            
            // Get sidebar width to avoid overlapping
            const sidebar = document.querySelector('.sidebar');
            const sidebarWidth = sidebar ? sidebar.getBoundingClientRect().width : 250;
            
            if (position === 'right') {
                box.style.top = (rect.top + rect.height/2 - boxRect.height/2) + 'px';
                box.style.left = (rect.right + 20) + 'px';
                box.style.transform = 'none';
            } else if (position === 'left') {
                // Position to the right of the sidebar but with enough space
                box.style.top = (rect.top + rect.height/2 - boxRect.height/2) + 'px';
                box.style.left = (sidebarWidth + 30) + 'px';
                box.style.transform = 'none';
            } else if (position === 'top') {
                box.style.top = (rect.top - boxRect.height - 20) + 'px';
                box.style.left = Math.max((rect.left + rect.width/2 - boxRect.width/2), sidebarWidth + 20) + 'px';
                box.style.transform = 'none';
            } else if (position === 'bottom') {
                box.style.top = (rect.bottom + 20) + 'px';
                box.style.left = Math.max((rect.left + rect.width/2 - boxRect.width/2), sidebarWidth + 20) + 'px';
                box.style.transform = 'none';
            }
            
            // Make sure the box stays within viewport
            const viewport = {
                top: 10,
                right: window.innerWidth - 10,
                bottom: window.innerHeight - 10,
                left: sidebarWidth + 10 // Ensure left edge doesn't overlap sidebar
            };
            
            const newBoxRect = box.getBoundingClientRect();
            
            if (newBoxRect.left < viewport.left) {
                box.style.left = viewport.left + 'px';
            }
            if (newBoxRect.right > viewport.right) {
                box.style.left = (viewport.right - newBoxRect.width) + 'px';
            }
            if (newBoxRect.top < viewport.top) {
                box.style.top = viewport.top + 'px';
            }
            if (newBoxRect.bottom > viewport.bottom) {
                box.style.top = (viewport.bottom - newBoxRect.height) + 'px';
            }
        }
        
        // Highlight target element
        function highlightElement(targetSelector) {
            // Remove previous highlighting
            document.querySelectorAll('.tour-highlighted-element').forEach(el => {
                el.classList.remove('tour-highlighted-element');
                el.style.zIndex = '';
                el.style.position = '';
                el.style.outline = '';
                el.style.backgroundColor = '';
            });
            
            if (!targetSelector) {
                highlight.style.display = 'none';
                return null;
            }
            
            // Try multiple selectors (comma-separated)
            let targetElement = null;
            const selectors = targetSelector.split(',');
            
            for (const selector of selectors) {
                const trimmedSelector = selector.trim();
                const element = document.querySelector(trimmedSelector);
                if (element) {
                    console.log('Found element with selector:', trimmedSelector);
                    targetElement = element;
                    break;
                }
            }
            
            if (!targetElement) {
                console.log('Target element not found for any selector in:', targetSelector);
                highlight.style.display = 'none';
                return null;
            }
            
            // Special handling for sidebar navigation items
            let isNavItem = false;
            let isMainNav = false;
            let isUserNav = false;
            
            if (targetElement.closest('.main-nav li')) {
                isNavItem = true;
                isMainNav = true;
                
                // Target both the li and the a element for better highlighting
                const li = targetElement.closest('li');
                if (li && targetElement.tagName !== 'LI') {
                    li.classList.add('tour-highlighted-element');
                    
                    // Also highlight the anchor tag itself (important!)
                    const anchor = li.querySelector('a');
                    if (anchor) {
                        anchor.classList.add('tour-highlighted-element');
                        // Apply explicit styles to ensure visibility
                        anchor.style.backgroundColor = 'rgba(118, 105, 178, 0.3)';
                        anchor.style.borderRadius = '8px';
                        anchor.style.zIndex = '9999';
                    }
                }
                
                // If we're targeting the a directly, make sure it's highlighted
                if (targetElement.tagName === 'A') {
                    targetElement.style.backgroundColor = 'rgba(118, 105, 178, 0.3)';
                    targetElement.style.borderRadius = '8px';
                    targetElement.style.zIndex = '9999';
                }
            } else if (targetElement.closest('.user-nav')) {
                isUserNav = true;
            } else if (targetElement.classList.contains('sidebar') || targetElement.tagName === 'ASIDE') {
                // For the entire sidebar, we want a different style of highlighting
                isMainNav = true;
            }
            
            // Highlight the element
            highlight.style.display = 'block';
            
            // Position highlight element
            const rect = targetElement.getBoundingClientRect();
            highlight.style.top = rect.top + 'px';
            highlight.style.left = rect.left + 'px';
            highlight.style.width = rect.width + 'px';
            highlight.style.height = rect.height + 'px';
            
            // Make element more prominent
            targetElement.classList.add('tour-highlighted-element');
            
            // Store the original styles
            const originalZIndex = targetElement.style.zIndex;
            const originalPosition = targetElement.style.position;
            const originalBg = targetElement.style.backgroundColor;
            
            // Make sure the highlighted element is visible, but handle special cases
            if (!isNavItem && !isMainNav && !isUserNav) {
                // For normal elements
                if (!targetElement.style.position || targetElement.style.position === 'static') {
                    targetElement.style.position = 'relative';
                }
                targetElement.style.zIndex = '9999';
                targetElement.style.outline = '3px solid #7669b2';
            } else if (isNavItem) {
                // For navigation items, let CSS handle it mostly
                // Just ensure they're visible
                targetElement.style.zIndex = '9999';
                
                // Make the text white for better visibility
                const spans = targetElement.querySelectorAll('span');
                spans.forEach(span => {
                    span.style.color = 'white';
                    span.style.fontWeight = 'bold';
                });
            }
            
            // Add a data attribute to track original styles
            targetElement.setAttribute('data-original-zindex', originalZIndex);
            targetElement.setAttribute('data-original-position', originalPosition);
            targetElement.setAttribute('data-original-bg', originalBg);
            
            return targetElement;
        }
        
        // Update the entire tour step (highlight, position, content)
        function updateTourStep(stepIndex) {
            const step = steps[stepIndex];
            console.log(`Updating to step ${stepIndex + 1}/${steps.length}: ${step.title}`);
            
            // First highlight the target element
            const targetElement = highlightElement(step.target);
            
            // Then position the tour box
            positionTourBox(tourBox, step.position, targetElement);
            
            // Finally update content
            updateTourContent(tourBox, step);
        }
        
        // Update tour content
        function updateTourContent(box, step) {
            box.innerHTML = `
                <div style="margin-bottom: 15px;">
                    <h3 style="color: #1b309a; margin-top: 0; margin-bottom: 5px;">${step.title}</h3>
                    <p style="color: #555; margin: 0;">${step.text}</p>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    ${currentStep > 0 ? 
                        '<button id="tour-prev" style="background-color: transparent; color: #555; border: 1px solid #d1d5db; border-radius: 4px; padding: 6px 12px; cursor: pointer;">Back</button>' : 
                        '<div style="width: 50px;"></div>'}
                    <div style="display: flex; gap: 5px; align-items: center;">
                        ${steps.map((_, index) => 
                            `<span style="width: 8px; height: 8px; display: inline-block; border-radius: 50%; background-color: ${index === currentStep ? '#1b309a' : '#d1d5db'};"></span>`
                        ).join('')}
                    </div>
                    <button id="tour-next" style="background-color: #1b309a; color: white; border: none; border-radius: 4px; padding: 6px 12px; cursor: pointer;">
                        ${currentStep === steps.length - 1 ? 'Finish' : 'Next'}
                    </button>
                </div>
                <button id="tour-close" style="position: absolute; top: 10px; right: 10px; background: transparent; border: none; font-size: 18px; cursor: pointer;">&times;</button>
            `;
            
            // Add event listeners using a small delay to ensure DOM is fully updated
            setTimeout(() => {
                const nextBtn = document.getElementById('tour-next');
                const closeBtn = document.getElementById('tour-close');
                
                if (nextBtn) nextBtn.addEventListener('click', nextStep);
                if (closeBtn) closeBtn.addEventListener('click', closeTour);
                
                if (currentStep > 0) {
                    const prevBtn = document.getElementById('tour-prev');
                    if (prevBtn) prevBtn.addEventListener('click', prevStep);
                }
                
                console.log('Updated tour content for step', currentStep + 1);
            }, 50);
        }
    }
    
    // Check if it's a new user
    function checkNewUser() {
        const urlParams = new URLSearchParams(window.location.search);
        const isNewUser = urlParams.get('new_user') === 'true';
        
        if (isNewUser) {
            console.log('New user detected, showing welcome screen');
            // Store in localStorage that user has seen tour
            localStorage.setItem('desiq_new_user', 'true');
            createSimpleTour();
        }
    }
    
    // Hide tour button if present
    function hideTourButton() {
        const tourButton = document.querySelector('.tour-button');
        if (tourButton) {
            console.log('Hiding tour button');
            tourButton.style.display = 'none';
            tourButton.classList.add('hidden');
        }
    }
    
    // Add a tour button to dashboard
    function addTourButton() {
        // Check if the tour has been completed
        const tourCompleted = localStorage.getItem('desiq_tour_completed') === 'true';
        
        if (tourCompleted) {
            console.log('Tour already completed, not showing tour button');
            return;
        }
        
        // Check if we're on the dashboard page using multiple methods
        const isDashboardUrl = window.location.pathname.includes('/dashboard') || 
                              window.location.href.includes('/dashboard');
        
        // Check if the URL name is dashboard or if there's an active dashboard link in the menu
        const isDashboardActive = document.querySelector('.main-nav li.active a[href*="dashboard"]') !== null;
        
        // Get the page header text
        const pageHeader = document.querySelector('.page-header h1');
        const isDashboardHeader = pageHeader && 
                                 (pageHeader.textContent.toLowerCase().includes('dashboard') ||
                                  pageHeader.textContent.trim() === 'Dashboard');
        
        // Combined check
        const isDashboard = isDashboardUrl || isDashboardActive || isDashboardHeader;
        
        console.log('Is dashboard page:', isDashboard);
        
        const dashboard = document.querySelector('.dashboard-header, .page-header');
        if (dashboard && !document.querySelector('.tour-button') && isDashboard) {
            console.log('Adding tour button to dashboard');
            const tourButton = document.createElement('button');
            tourButton.className = 'tour-button';
            tourButton.innerHTML = `
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 5px;"><circle cx="12" cy="12" r="10"></circle><path d="M12 16v-4"></path><path d="M12 8h.01"></path></svg>
                Take Tour
            `;
            tourButton.addEventListener('click', createSimpleTour);
            dashboard.appendChild(tourButton);
        }
    }
    
    // Initialize
    console.log('Initializing tour');
    setTimeout(function() {
        // Add IDs to navigation initially
        addNavIDs();
        
        // Check if tour is completed and add class to body
        checkTourCompleted();
        
        checkNewUser();
        addTourButton();
        
        // Make sure the global function is available
        window.startDesiQTour = createSimpleTour;
        console.log('Tour initialization complete');
    }, 500);
}); 
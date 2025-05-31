document.addEventListener('DOMContentLoaded', function() {
    // Account Settings Form
    const accountForm = document.getElementById('account-form');
    const nameInput = document.querySelector('input[name="name"]');
    const emailInput = document.querySelector('input[name="email"]');
    const mbtiSelect = document.querySelector('select[name="mbti_type"]');
    const decisionStyleSelect = document.querySelector('select[name="decision_style"]');
    const primaryBiasSelect = document.querySelector('select[name="primary_bias"]');
    const accountSaveBtn = document.querySelector('.overlap-5');
    
    if (accountSaveBtn && accountForm) {
        accountSaveBtn.addEventListener('click', function() {
            // Create hidden inputs for form submission
            const nameHidden = document.createElement('input');
            nameHidden.type = 'hidden';
            nameHidden.name = 'name';
            nameHidden.value = nameInput.value;
            accountForm.appendChild(nameHidden);
            
            const emailHidden = document.createElement('input');
            emailHidden.type = 'hidden';
            emailHidden.name = 'email';
            emailHidden.value = emailInput.value;
            accountForm.appendChild(emailHidden);
            
            const mbtiHidden = document.createElement('input');
            mbtiHidden.type = 'hidden';
            mbtiHidden.name = 'mbti_type';
            mbtiHidden.value = mbtiSelect.value;
            accountForm.appendChild(mbtiHidden);
            
            const decisionStyleHidden = document.createElement('input');
            decisionStyleHidden.type = 'hidden';
            decisionStyleHidden.name = 'decision_style';
            decisionStyleHidden.value = decisionStyleSelect.value;
            accountForm.appendChild(decisionStyleHidden);
            
            const primaryBiasHidden = document.createElement('input');
            primaryBiasHidden.type = 'hidden';
            primaryBiasHidden.name = 'primary_bias';
            primaryBiasHidden.value = primaryBiasSelect.value;
            accountForm.appendChild(primaryBiasHidden);
            
            // Submit the form
            accountForm.submit();
        });
    }
    
    // Password Form
    const passwordForm = document.getElementById('password-form');
    const currentPasswordInput = document.querySelector('input[name="current_password"]');
    const newPasswordInput = document.querySelector('input[name="new_password"]');
    const confirmPasswordInput = document.querySelector('input[name="confirm_password"]');
    const passwordSaveBtn = document.querySelector('.overlap-7');
    
    if (passwordSaveBtn && passwordForm) {
        passwordSaveBtn.addEventListener('click', function() {
            // Validate passwords match
            if(newPasswordInput.value !== confirmPasswordInput.value) {
                alert('New passwords do not match!');
                return;
            }
            
            // Create hidden inputs for form submission
            const currentPasswordHidden = document.createElement('input');
            currentPasswordHidden.type = 'hidden';
            currentPasswordHidden.name = 'current_password';
            currentPasswordHidden.value = currentPasswordInput.value;
            passwordForm.appendChild(currentPasswordHidden);
            
            const newPasswordHidden = document.createElement('input');
            newPasswordHidden.type = 'hidden';
            newPasswordHidden.name = 'new_password';
            newPasswordHidden.value = newPasswordInput.value;
            passwordForm.appendChild(newPasswordHidden);
            
            const confirmPasswordHidden = document.createElement('input');
            confirmPasswordHidden.type = 'hidden';
            confirmPasswordHidden.name = 'confirm_password';
            confirmPasswordHidden.value = confirmPasswordInput.value;
            passwordForm.appendChild(confirmPasswordHidden);
            
            // Submit the form
            passwordForm.submit();
        });
    }
    
    // Preferences Form (Theme and Language)
    const preferencesForm = document.getElementById('preferences-form');
    const themeSelect = document.querySelector('select[name="theme"]');
    const languageSelect = document.querySelector('select[name="language"]');
    
    if (themeSelect && preferencesForm) {
        // Auto-submit when theme changes
        themeSelect.addEventListener('change', function() {
            const themeHidden = document.createElement('input');
            themeHidden.type = 'hidden';
            themeHidden.name = 'theme';
            themeHidden.value = themeSelect.value;
            preferencesForm.appendChild(themeHidden);
            
            // Add language value too
            const languageHidden = document.createElement('input');
            languageHidden.type = 'hidden';
            languageHidden.name = 'language';
            languageHidden.value = languageSelect.value;
            preferencesForm.appendChild(languageHidden);
            
            preferencesForm.submit();
        });
    }
    
    if (languageSelect && preferencesForm) {
        // Auto-submit when language changes
        languageSelect.addEventListener('change', function() {
            const languageHidden = document.createElement('input');
            languageHidden.type = 'hidden';
            languageHidden.name = 'language';
            languageHidden.value = languageSelect.value;
            preferencesForm.appendChild(languageHidden);
            
            // Add theme value too
            const themeHidden = document.createElement('input');
            themeHidden.type = 'hidden';
            themeHidden.name = 'theme';
            themeHidden.value = themeSelect.value;
            preferencesForm.appendChild(themeHidden);
            
            preferencesForm.submit();
        });
    }
    
    // Form validation
    function validateEmail(email) {
        const re = /^(([^<>()\[\]\\.,;:\s@"]+(\.[^<>()\[\]\\.,;:\s@"]+)*)|(".+"))@((\[[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}\.[0-9]{1,3}])|(([a-zA-Z\-0-9]+\.)+[a-zA-Z]{2,}))$/;
        return re.test(String(email).toLowerCase());
    }
    
    if (accountForm) {
        accountForm.addEventListener('submit', function(event) {
            if (!validateEmail(emailInput.value)) {
                event.preventDefault();
                alert('Please enter a valid email address.');
                return false;
            }
            
            if (nameInput.value.trim() === '') {
                event.preventDefault();
                alert('Name cannot be empty.');
                return false;
            }
        });
    }
    
    if (passwordForm) {
        passwordForm.addEventListener('submit', function(event) {
            if (currentPasswordInput.value.trim() === '') {
                event.preventDefault();
                alert('Current password is required.');
                return false;
            }
            
            if (newPasswordInput.value.trim() === '') {
                event.preventDefault();
                alert('New password cannot be empty.');
                return false;
            }
            
            if (newPasswordInput.value.length < 8) {
                event.preventDefault();
                alert('Password must be at least 8 characters long.');
                return false;
            }
        });
    }
});
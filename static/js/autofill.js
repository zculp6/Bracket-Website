/* =========================================================
   AUTOFILL.JS
   Handles bracket autofill, selection tracking,
   and bracket submission logic.
   ========================================================= */

/* ---------------------------------------------------------
   SELECT TEAM (manual click — called by bracket.js)
   --------------------------------------------------------- */
function selectTeam(teamId) {
    console.log(`Team ${teamId} selected`);
}

/* ---------------------------------------------------------
   AUTOFILL BRACKET
   Sends strategy to /autofill_bracket, receives bracket
   data and populates the UI via bracket.js's autofillBracket()
   --------------------------------------------------------- */
function requestAutofill(strategy) {
    if (!strategy || strategy === 'none') {
        alert('Please choose an autofill strategy first.');
        return;
    }

    fetch('/autofill_bracket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ strategy })
    })
    .then(response => {
        if (!response.ok) throw new Error('Server error: ' + response.status);
        return response.json();
    })
    .then(data => {
        if (typeof autofillBracket === 'function') {
            autofillBracket(data);
        } else {
            console.error('autofillBracket() not found. Make sure bracket.js is loaded first.');
        }
    })
    .catch(err => {
        console.error('Autofill failed:', err);
        alert('Failed to autofill bracket. Please try again.');
    });
}

/* ---------------------------------------------------------
   GET USER SELECTIONS
   Collects all selected (winning) teams from the DOM,
   returning a structured object keyed by round container ID.
   --------------------------------------------------------- */
function getUserSelections() {
    const result = {};

    document.querySelectorAll('.matchups').forEach(roundElem => {
        const id = roundElem.id;
        if (!id) return;

        const picks = [];
        roundElem.querySelectorAll('.matchup').forEach(matchup => {
            const selected = matchup.querySelector('.team.selected');
            picks.push(selected ? selected.getAttribute('data-name') : null);
        });

        result[id] = picks;
    });

    // Champion
    const champElem = document.getElementById('champion');
    result['champion'] = champElem ? champElem.innerText.trim() : null;

    return result;
}

/* ---------------------------------------------------------
   VALIDATE BRACKET
   Returns an array of warning strings for incomplete picks.
   --------------------------------------------------------- */
function validateBracket(bracketData) {
    const warnings = [];

    for (const [roundId, picks] of Object.entries(bracketData)) {
        if (roundId === 'champion') {
            if (!picks) warnings.push('No National Champion selected.');
            continue;
        }

        const nullCount = picks.filter(p => p === null).length;
        if (nullCount > 0) {
            warnings.push(`${nullCount} pick(s) missing in: ${roundId}`);
        }
    }

    return warnings;
}

/* ---------------------------------------------------------
   GET CURRENT USER ID
   Reads from a meta tag or a global variable set by Flask.
   --------------------------------------------------------- */
function getUserId() {
    // Option 1: meta tag — add <meta name="user-id" content="{{ current_user.id }}"> to bracket.html
    const meta = document.querySelector('meta[name="user-id"]');
    if (meta) return meta.getAttribute('content');

    // Option 2: global JS var set by Flask template
    if (typeof CURRENT_USER_ID !== 'undefined') return CURRENT_USER_ID;

    // Fallback
    return null;
}

/* ---------------------------------------------------------
   SUBMIT BRACKET
   Validates, then POSTs bracket data to /submit_bracket.
   --------------------------------------------------------- */
function submitBracket() {
    const bracketData = getUserSelections();
    const warnings = validateBracket(bracketData);

    if (warnings.length > 0) {
        const proceed = confirm(
            `Your bracket has incomplete picks:\n\n` +
            warnings.join('\n') +
            `\n\nSubmit anyway?`
        );
        if (!proceed) return;
    }

    const userId = getUserId();

    const submitBtn = document.getElementById('submitBracketButton');
    if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Submitting...';
    }

    fetch('/submit_bracket', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            user_id: userId,
            bracket: bracketData
        })
    })
    .then(response => {
        if (!response.ok) throw new Error('Server error: ' + response.status);
        return response.json();
    })
    .then(data => {
        alert(data.message || 'Bracket submitted successfully!');
    })
    .finally(() => {
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.textContent = 'Submit Bracket';
        }
    });
}

/* ---------------------------------------------------------
   WIRE UP BUTTONS (runs after DOM is ready)
   --------------------------------------------------------- */
document.addEventListener('DOMContentLoaded', function () {

    // Autofill button
    const autofillBtn = document.getElementById('autofillButton');
    if (autofillBtn) {
        autofillBtn.addEventListener('click', function () {
            const strategy = document.getElementById('autofillStrategy')?.value;
            requestAutofill(strategy);
        });
    }

    // Submit button
    const submitBtn = document.getElementById('submitBracketButton');
    if (submitBtn) {
        submitBtn.addEventListener('click', submitBracket);
    }

});

console.log('Autofill JS loaded.');

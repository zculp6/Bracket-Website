
/* =========================================================
   TEAM ROW TEMPLATE
   ========================================================= */
function createTeamRow(seed, name) {
    return `<div class="team" data-seed="${seed}" data-name="${name}">
                <span class="seed">${seed}</span>
                <span class="team-name">${name}</span>
            </div>`;
}

/* =========================================================
   LOAD INITIAL ROUND OF 64 TEAMS
   Called once on page load with data from Flask.
   teamsData = { west: [{seed, name}, ...], south: ..., east: ..., midwest: ... }
   ========================================================= */
function loadInitialTeams(teamsData) {
    console.log("Loading initial bracket teams...");

    ["west", "south", "east", "midwest"].forEach(region => {
        const teams  = teamsData[region] || [];
        const target = document.getElementById(`${region}_r64`);
        if (!target) { console.warn(`Missing container: ${region}_r64`); return; }

        target.innerHTML = "";

        for (let i = 0; i + 1 < teams.length; i += 2) {
            const div = document.createElement("div");
            div.className = "matchup";
            div.innerHTML = createTeamRow(teams[i].seed, teams[i].name)
                          + createTeamRow(teams[i+1].seed, teams[i+1].name);
            target.appendChild(div);
        }
    });

    attachClickHandlers();
}

/* =========================================================
   ATTACH CLICK HANDLERS
   Replaces every .team element with a fresh clone to avoid
   stacking duplicate listeners on re-renders.
   ========================================================= */
function attachClickHandlers() {
    document.querySelectorAll(".team").forEach(oldTeam => {
        const newTeam = oldTeam.cloneNode(true);
        oldTeam.parentNode.replaceChild(newTeam, oldTeam);

        newTeam.addEventListener("click", function () {
            const matchup = this.closest(".matchup");
            if (!matchup) return;

            // Deselect sibling, select this
            matchup.querySelectorAll(".team").forEach(t => {
                t.classList.remove("selected");
                t.classList.remove("eliminated");
            });
            this.classList.add("selected");

            // Mark loser
            matchup.querySelectorAll(".team").forEach(t => {
                if (t !== this) t.classList.add("eliminated");
            });

            advanceTeam(matchup, {
                seed: this.getAttribute("data-seed"),
                name: this.getAttribute("data-name")
            });
        });
    });
}

/* =========================================================
   FIND REGION & ROUND FROM A MATCHUP ELEMENT
   The matchup's parent is the .matchups container whose id
   is like "west_r64", "ff_left", "championship", etc.
   ========================================================= */
function getContainerId(matchupElem) {
    const container = matchupElem.closest(".matchups");
    return container ? container.id : null;
}

function findRegionFromMatchup(matchupElem) {
    const id = getContainerId(matchupElem);
    if (!id) return null;
    return id.split("_")[0];   // "west_r64" → "west"
}

function findRoundFromMatchup(matchupElem) {
    const id = getContainerId(matchupElem);
    if (!id) return null;
    // handles "west_r64", "ff_left", "championship"
    const parts = id.split("_");
    return parts.length > 1 ? parts.slice(1).join("_") : id;
}

/* =========================================================
   GET NEXT ROUND CONTAINER ID
   ========================================================= */
function getNextRoundId(region, round) {
    const regionRounds = ["r64", "r32", "s16", "e8"];
    const idx = regionRounds.indexOf(round);

    // Inside a region → next region round
    if (idx !== -1 && idx < regionRounds.length - 1) {
        return `${region}_${regionRounds[idx + 1]}`;
    }

    // Elite 8 → Final Four
    if (round === "e8") {
        return (region === "west" || region === "south") ? "ff_left" : "ff_right";
    }

    // Final Four → Championship
    if (round === "left" || round === "right") {
        return "championship";
    }

    // Championship → Champion display
    if (region === "championship") {
        return "champion_display";
    }

    return null;
}

/* =========================================================
   ADVANCE WINNER TO NEXT ROUND
   ========================================================= */
function advanceTeam(matchupElem, teamObj) {
    const region    = findRegionFromMatchup(matchupElem);
    const round     = findRoundFromMatchup(matchupElem);
    const nextId    = getNextRoundId(region, round);

    if (!nextId) return;

    // Special case: champion display div
    if (nextId === "champion_display") {
        const champDiv = document.getElementById("champion");
        if (champDiv) champDiv.innerText = `${teamObj.seed} ${teamObj.name}`;
        return;
    }

    const nextContainer = document.getElementById(nextId);
    if (!nextContainer) { console.warn("Missing next container:", nextId); return; }

    // Figure out which slot this matchup feeds into.
    // Each pair of matchups in the current round feeds one matchup in the next round.
    const currentContainer = matchupElem.closest(".matchups");
    const allMatchups       = Array.from(currentContainer.querySelectorAll(".matchup"));
    const matchupIndex      = allMatchups.indexOf(matchupElem);
    const nextMatchupIndex  = Math.floor(matchupIndex / 2);  // pairs feed one slot
    const slotPosition      = matchupIndex % 2;              // 0 = top team, 1 = bottom team

    // Ensure enough matchup divs exist in next round
    let nextMatchups = nextContainer.querySelectorAll(".matchup");
    while (nextMatchups.length <= nextMatchupIndex) {
        const div = document.createElement("div");
        div.className = "matchup";
        nextContainer.appendChild(div);
        nextMatchups = nextContainer.querySelectorAll(".matchup");
    }

    const targetMatchup = nextMatchups[nextMatchupIndex];

    // Remove any previously placed team in this slot position
    const existingTeams = targetMatchup.querySelectorAll(".team");
    if (existingTeams[slotPosition]) {
        existingTeams[slotPosition].remove();
    }

    // Insert at correct slot position
    const newRow = document.createElement("div");
    newRow.className = "team";
    newRow.setAttribute("data-seed", teamObj.seed);
    newRow.setAttribute("data-name", teamObj.name);
    newRow.innerHTML = `<span class="seed">${teamObj.seed}</span>
                        <span class="team-name">${teamObj.name}</span>`;

    const currentTeams = targetMatchup.querySelectorAll(".team");
    if (slotPosition === 0 || currentTeams.length === 0) {
        targetMatchup.insertBefore(newRow, targetMatchup.firstChild);
    } else {
        targetMatchup.appendChild(newRow);
    }

    attachClickHandlers();
}

/* =========================================================
   AUTOFILL BRACKET
   Accepts the full bracket object from the /autofill_bracket
   endpoint (which now returns all rounds, not just round_1).
   ========================================================= */
function autofillBracket(data) {
    // Clear all round containers first
    const allContainers = [
        "west_r64","west_r32","west_s16","west_e8",
        "south_r64","south_r32","south_s16","south_e8",
        "east_r64","east_r32","east_s16","east_e8",
        "midwest_r64","midwest_r32","midwest_s16","midwest_e8",
        "ff_left","ff_right","championship"
    ];
    allContainers.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = "";
    });

    const champDiv = document.getElementById("champion");
    if (champDiv) champDiv.innerText = "";

    // Populate each container
    allContainers.forEach(containerId => {
        const teams = data[containerId];
        if (!teams || teams.length === 0) return;

        const container = document.getElementById(containerId);
        if (!container) return;

        for (let i = 0; i + 1 < teams.length; i += 2) {
            const div = document.createElement("div");
            div.className = "matchup";
            div.innerHTML = createTeamRow(teams[i].seed, teams[i].name)
                          + createTeamRow(teams[i+1].seed, teams[i+1].name);

            // Mark simulated winner (first of each pair is the winner from simulation)
            // We store the winner name in data as well if provided
            container.appendChild(div);
        }
    });

    // Set champion
    if (data.champion) {
        if (champDiv) champDiv.innerText = data.champion;
    }

    attachClickHandlers();
}

/* =========================================================
   BUILD JSON FOR SUBMISSION
   ========================================================= */
function buildBracketJSON() {
    const result = {};

    document.querySelectorAll(".matchups").forEach(roundElem => {
        const id = roundElem.id;
        if (!id) return;

        const matchups = [];
        roundElem.querySelectorAll(".matchup").forEach(m => {
            const selected = m.querySelector(".team.selected");
            matchups.push(selected ? selected.getAttribute("data-name") : null);
        });

        result[id] = matchups;
    });

    const champDiv = document.getElementById("champion");
    result["champion"] = champDiv ? champDiv.innerText.trim() : null;

    return result;
}

console.log("Bracket JS loaded.");
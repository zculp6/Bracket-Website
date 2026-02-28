/* =========================================================
   TEAM ROW TEMPLATE
   ========================================================= */
function createTeamRow(seed, name, isSelected = false, isEliminated = false) {
    let classes = "team";
    if (isSelected)   classes += " selected";
    if (isEliminated) classes += " eliminated";
    return `<div class="${classes}" data-seed="${seed}" data-name="${name}">
                <span class="seed">${seed}</span>
                <span class="team-name">${name}</span>
            </div>`;
}

/* =========================================================
   BLANK PLACEHOLDER ROW
   ========================================================= */
function createBlankTeamRow() {
    return `<div class="team team-placeholder" data-seed="" data-name="">
                <span class="seed"></span>
                <span class="team-name">TBD</span>
            </div>`;
}

/* =========================================================
   PRE-FILL DOWNSTREAM ROUNDS WITH BLANK MATCHUPS
   Ensures bracket structure is always fully present so
   layout never collapses while teams are being picked.
   ========================================================= */
function preFillBlankMatchups() {
    // Regional rounds: r32=4 matchups, s16=2, e8=1
    const roundCounts = { r32: 4, s16: 2, e8: 1 };
    ["west", "south", "east", "midwest"].forEach(region => {
        Object.entries(roundCounts).forEach(([round, count]) => {
            const container = document.getElementById(`${region}_${round}`);
            if (!container) return;
            container.innerHTML = "";
            for (let i = 0; i < count; i++) {
                const div = document.createElement("div");
                div.className = "matchup";
                div.innerHTML = createBlankTeamRow() + createBlankTeamRow();
                container.appendChild(div);
            }
        });
    });

    // Final Four semi-finals (1 matchup each)
    ["ff_left", "ff_right"].forEach(id => {
        const container = document.getElementById(id);
        if (!container) return;
        container.innerHTML = "";
        const div = document.createElement("div");
        div.className = "matchup";
        div.innerHTML = createBlankTeamRow() + createBlankTeamRow();
        container.appendChild(div);
    });

    // Championship (1 matchup)
    const champContainer = document.getElementById("championship");
    if (champContainer) {
        champContainer.innerHTML = "";
        const div = document.createElement("div");
        div.className = "matchup";
        div.innerHTML = createBlankTeamRow() + createBlankTeamRow();
        champContainer.appendChild(div);
    }
}

/* =========================================================
   LOAD INITIAL ROUND OF 64 TEAMS
   ========================================================= */
function loadInitialTeams(teamsData) {
    ["west", "south", "east", "midwest"].forEach(region => {
        const teams  = teamsData[region] || [];
        const target = document.getElementById(`${region}_r64`);
        if (!target) return;
        target.innerHTML = "";
        for (let i = 0; i + 1 < teams.length; i += 2) {
            const div = document.createElement("div");
            div.className = "matchup";
            div.innerHTML = createTeamRow(teams[i].seed, teams[i].name)
                          + createTeamRow(teams[i+1].seed, teams[i+1].name);
            target.appendChild(div);
        }
    });

    // Pre-populate all downstream rounds with blank placeholder matchups
    preFillBlankMatchups();
    
    if (!window.__regionTabsInitialized) {
        initRegionTabs();
        window.__regionTabsInitialized = true;
    }

    attachClickHandlers();
}

/* =========================================================
   ATTACH CLICK HANDLERS
   ========================================================= */
function attachClickHandlers() {
    document.querySelectorAll(".team").forEach(oldTeam => {
        const newTeam = oldTeam.cloneNode(true);
        oldTeam.parentNode.replaceChild(newTeam, oldTeam);

        // Placeholders are not clickable
        if (newTeam.classList.contains("team-placeholder")) return;

        newTeam.addEventListener("click", function () {
            const matchup = this.closest(".matchup");
            if (!matchup) return;
            matchup.querySelectorAll(".team").forEach(t => {
                t.classList.remove("selected", "eliminated");
            });
            this.classList.add("selected");
            matchup.querySelectorAll(".team:not(.selected)").forEach(t => {
                t.classList.add("eliminated");
            });
            advanceTeam(matchup, {
                seed: this.getAttribute("data-seed"),
                name: this.getAttribute("data-name")
            });
        });
    });
}

/* =========================================================
   NAVIGATION HELPERS
   ========================================================= */
function getContainerId(matchupElem) {
    const c = matchupElem.closest(".matchups");
    return c ? c.id : null;
}

function getRegion(matchupElem) {
    const id = getContainerId(matchupElem);
    return id ? id.split("_")[0] : null;
}

function getRound(matchupElem) {
    const id = getContainerId(matchupElem);
    if (!id) return null;
    const parts = id.split("_");
    return parts.length >= 2 ? parts.slice(1).join("_") : id;
}

function getNextSlot(matchupElem) {
    const containerId = getContainerId(matchupElem);
    const region      = getRegion(matchupElem);
    const round       = getRound(matchupElem);

    const container   = matchupElem.closest(".matchups");
    const allMatchups = Array.from(container.querySelectorAll(":scope > .matchup"));
    const matchupIdx  = allMatchups.indexOf(matchupElem);

    const regionRounds = ["r64", "r32", "s16", "e8"];
    const roundIdx     = regionRounds.indexOf(round);

    if (roundIdx !== -1 && roundIdx < regionRounds.length - 1) {
        return {
            nextContainerId: `${region}_${regionRounds[roundIdx + 1]}`,
            slotIndex:       Math.floor(matchupIdx / 2),
            teamSlot:        matchupIdx % 2
        };
    }

    if (round === "e8") {
        if (region === "west")    return { nextContainerId: "ff_left",  slotIndex: 0, teamSlot: 0 };
        if (region === "south")   return { nextContainerId: "ff_left",  slotIndex: 0, teamSlot: 1 };
        if (region === "east")    return { nextContainerId: "ff_right", slotIndex: 0, teamSlot: 0 };
        if (region === "midwest") return { nextContainerId: "ff_right", slotIndex: 0, teamSlot: 1 };
    }

    if (round === "left")  return { nextContainerId: "championship", slotIndex: 0, teamSlot: 0 };
    if (round === "right") return { nextContainerId: "championship", slotIndex: 0, teamSlot: 1 };

    if (containerId === "championship") {
        return { nextContainerId: "champion_display", slotIndex: 0, teamSlot: 0 };
    }

    return null;
}

/* =========================================================
   REMOVE A TEAM FROM A SPECIFIC SLOT IN A MATCHUP CONTAINER
   Replaces it with a blank placeholder. Used during cascade removal.
   ========================================================= */
function removeTeamFromSlot(containerId, slotIndex, teamSlot) {
    if (containerId === "champion_display") {
        const el = document.getElementById("champion");
        if (el) el.innerText = "";
        return;
    }

    const container = document.getElementById(containerId);
    if (!container) return;

    const matchups = container.querySelectorAll(":scope > .matchup");
    if (matchups.length <= slotIndex) return;

    const targetMatchup = matchups[slotIndex];
    const existingTeams = targetMatchup.querySelectorAll(":scope > .team");
    const teamEl = existingTeams[teamSlot];
    if (!teamEl || teamEl.classList.contains("team-placeholder")) return;

    // Replace with blank placeholder
    const blank = document.createElement("div");
    blank.className = "team team-placeholder";
    blank.setAttribute("data-seed", "");
    blank.setAttribute("data-name", "");
    blank.innerHTML = `<span class="seed"></span><span class="team-name">TBD</span>`;
    targetMatchup.replaceChild(blank, teamEl);
}

/* =========================================================
   CASCADE REMOVE A TEAM FROM ALL DOWNSTREAM ROUNDS
   Walks forward from a given slot, removing the specified team
   name wherever it appears as a winner in subsequent rounds.
   Also clears selected/eliminated state in the matchup where
   it was removed, so the other team is no longer "eliminated".
   ========================================================= */
function cascadeRemove(teamName, containerId, slotIndex, teamSlot) {
    if (!teamName) return;

    // Remove from the next-round slot
    removeTeamFromSlot(containerId, slotIndex, teamSlot);

    // Check if the team had won from this next-round matchup too —
    // i.e. was it selected in the matchup we just blanked? If so,
    // also un-eliminate the other team in that matchup, and recurse.
    if (containerId === "champion_display") return;

    const container = document.getElementById(containerId);
    if (!container) return;

    const matchups = container.querySelectorAll(":scope > .matchup");
    if (matchups.length <= slotIndex) return;

    const targetMatchup = matchups[slotIndex];

    // Was this team selected (winner) in this matchup?
    // After removal above it's now a placeholder, so check by name before removal.
    // We detect this by checking if the OTHER team in this matchup is "eliminated" —
    // meaning teamName was the selected winner here.
    const teams = targetMatchup.querySelectorAll(":scope > .team");
    const otherTeam = Array.from(teams).find(t =>
        t.getAttribute("data-name") !== teamName &&
        !t.classList.contains("team-placeholder")
    );

    // Check if teamName was the winner of this matchup by seeing if it was selected
    // We need to check the slot we just blanked — but since we already replaced it,
    // detect by checking if any remaining team is "eliminated" (means teamName was selected)
    const hasEliminated = Array.from(teams).some(t => t.classList.contains("eliminated"));

    if (hasEliminated) {
        // teamName was the winner here — un-eliminate the other team
        teams.forEach(t => t.classList.remove("eliminated", "selected"));

        // Find what the next slot for this matchup would be, and recurse
        const fakeMatchup = targetMatchup; // use it to compute next slot
        const nextSlot = getNextSlot(fakeMatchup);
        if (nextSlot) {
            cascadeRemove(teamName, nextSlot.nextContainerId, nextSlot.slotIndex, nextSlot.teamSlot);
        }
    }
}

/* =========================================================
   ADVANCE WINNER TO NEXT ROUND
   Before placing the new winner, cascades-removes the old one
   from all downstream rounds so stale picks are cleaned up.
   ========================================================= */
function advanceTeam(matchupElem, teamObj) {
    const next = getNextSlot(matchupElem);
    if (!next) return;

    const { nextContainerId, slotIndex, teamSlot } = next;

    if (nextContainerId === "champion_display") {
        const el = document.getElementById("champion");
        if (el) el.innerText = `${teamObj.seed} ${teamObj.name}`;
        return;
    }

    const nextContainer = document.getElementById(nextContainerId);
    if (!nextContainer) return;

    const matchups = nextContainer.querySelectorAll(":scope > .matchup");
    if (matchups.length <= slotIndex) return;

    const targetMatchup = matchups[slotIndex];
    const existingTeams = targetMatchup.querySelectorAll(":scope > .team");

    // Find the team currently in this slot (could be a prior winner to evict)
    const existingInSlot = existingTeams[teamSlot];
    const evictedName = existingInSlot && !existingInSlot.classList.contains("team-placeholder")
        ? existingInSlot.getAttribute("data-name")
        : null;

    // If there was a different team here, cascade-remove it from all downstream rounds
    if (evictedName && evictedName !== teamObj.name) {
        // Find what next slot the evicted team would have advanced to from this matchup
        const evictedNextSlot = getNextSlot(targetMatchup);
        if (evictedNextSlot) {
            cascadeRemove(evictedName, evictedNextSlot.nextContainerId, evictedNextSlot.slotIndex, evictedNextSlot.teamSlot);
        }
        // Also clear champion if it was this team
        const champDiv = document.getElementById("champion");
        if (champDiv && champDiv.innerText.includes(evictedName)) {
            champDiv.innerText = "";
        }
    }

    // Place the new winner into the slot
    const newTeamEl = document.createElement("div");
    newTeamEl.className = "team";
    newTeamEl.setAttribute("data-seed", teamObj.seed);
    newTeamEl.setAttribute("data-name", teamObj.name);
    newTeamEl.innerHTML = `<span class="seed">${teamObj.seed}</span>
                           <span class="team-name">${teamObj.name}</span>`;

    if (teamSlot === 0) {
        if (existingTeams[0]) {
            targetMatchup.replaceChild(newTeamEl, existingTeams[0]);
        } else {
            targetMatchup.insertBefore(newTeamEl, targetMatchup.firstChild);
        }
    } else {
        if (existingTeams[1]) {
            targetMatchup.replaceChild(newTeamEl, existingTeams[1]);
        } else {
            targetMatchup.appendChild(newTeamEl);
        }
    }

    attachClickHandlers();
}

/* =========================================================
   AUTOFILL BRACKET
   ========================================================= */
function autofillBracket(data) {
    const allContainersIds = [
        "west_r64","west_r32","west_s16","west_e8",
        "south_r64","south_r32","south_s16","south_e8",
        "east_r64","east_r32","east_s16","east_e8",
        "midwest_r64","midwest_r32","midwest_s16","midwest_e8",
        "ff_left","ff_right","championship"
    ];

    const roundOrder = [
        ["west_r64","west_r32"], ["west_r32","west_s16"], ["west_s16","west_e8"], ["west_e8","ff_left"],
        ["south_r64","south_r32"], ["south_r32","south_s16"], ["south_s16","south_e8"], ["south_e8","ff_left"],
        ["east_r64","east_r32"], ["east_r32","east_s16"], ["east_s16","east_e8"], ["east_e8","ff_right"],
        ["midwest_r64","midwest_r32"], ["midwest_r32","midwest_s16"], ["midwest_s16","midwest_e8"], ["midwest_e8","ff_right"],
        ["ff_left","championship"], ["ff_right","championship"]
    ];

    allContainersIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = "";
    });

    const champDiv = document.getElementById("champion");
    if (champDiv) champDiv.innerText = "";

    allContainersIds.forEach(containerId => {
        const teams = data[containerId];
        if (!teams || teams.length === 0) return;

        const nextIds = roundOrder.filter(([cur]) => cur === containerId).map(([, nxt]) => nxt);
        const winnerNames = new Set();
        nextIds.forEach(nextId => {
            const nextTeams = data[nextId] || [];
            nextTeams.forEach(t => winnerNames.add(t.name));
        });

        if (containerId === "championship" && data.champion) {
            winnerNames.add(data.champion);
        }

        const container = document.getElementById(containerId);
        if (!container) return;
        for (let i = 0; i + 1 < teams.length; i += 2) {
            const t1 = teams[i];
            const t2 = teams[i + 1];
            const t1wins = winnerNames.has(t1.name);
            const t2wins = winnerNames.has(t2.name);
            const div = document.createElement("div");
            div.className = "matchup";
            div.innerHTML = createTeamRow(t1.seed, t1.name, t1wins, !t1wins && t2wins)
                          + createTeamRow(t2.seed, t2.name, t2wins, !t2wins && t1wins);
            container.appendChild(div);
        }
    });

    if (data.champion && champDiv) champDiv.innerText = data.champion;

    attachClickHandlers();
}

/* =========================================================
   RESET BRACKET
   Clears all picks and restores the blank placeholder structure.
   ========================================================= */
function resetBracket() {
    if (!confirm("Reset all picks? This cannot be undone.")) return;

    // Re-load R64 teams fresh (clears all selected/eliminated state)
    if (typeof initialTeams !== 'undefined') {
        loadInitialTeams(initialTeams);
    } else {
        // Fallback: just clear selected/eliminated classes from R64
        document.querySelectorAll(".team").forEach(t => {
            t.classList.remove("selected", "eliminated");
        });
        preFillBlankMatchups();
        attachClickHandlers();
    }

    // Clear champion display
    const champDiv = document.getElementById("champion");
    if (champDiv) champDiv.innerText = "";
}

/* =========================================================
   REGION TAB SWITCHING
   ========================================================= */
function initRegionTabs() {
    const tabs = document.querySelectorAll('.bracket-region-tab');
    const panels = document.querySelectorAll('.bracket-region-panel');
    if (!tabs.length || !panels.length) return;

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            const region = tab.getAttribute('data-region');
            if (!region) return;

            tabs.forEach(t => t.classList.remove('active'));
            panels.forEach(panel => panel.classList.remove('active'));

            tab.classList.add('active');
            const targetPanel = document.querySelector(`.bracket-region-panel[data-region="${region}"]`);
            if (targetPanel) targetPanel.classList.add('active');
        });
    });
}

/* =========================================================
   VALIDATE ALL PICKS
   Returns an object: { valid: bool, missing: string[] }
   Checks every real matchup has a selected winner.
   ========================================================= */
function validateAllPicks() {
    const missing = [];

    const roundLabels = {
        r64: "Round of 64", r32: "Round of 32",
        s16: "Sweet 16",    e8:  "Elite 8"
    };
    const regionLabels = {
        west: "West", south: "South", east: "East", midwest: "Midwest"
    };

    // Regional rounds
    ["west", "south", "east", "midwest"].forEach(region => {
        ["r64", "r32", "s16", "e8"].forEach(round => {
            const container = document.getElementById(`${region}_${round}`);
            if (!container) return;
            container.querySelectorAll(":scope > .matchup").forEach((matchup, i) => {
                // Skip fully blank placeholder matchups
                const teams = matchup.querySelectorAll(".team");
                const allBlank = Array.from(teams).every(t => t.classList.contains("team-placeholder"));
                if (allBlank) return;
                const hasWinner = matchup.querySelector(".team.selected");
                if (!hasWinner) {
                    missing.push(`${regionLabels[region]} — ${roundLabels[round]} (game ${i + 1})`);
                }
            });
        });
    });

    // Final Four semis
    ["ff_left", "ff_right"].forEach(id => {
        const container = document.getElementById(id);
        if (!container) return;
        container.querySelectorAll(":scope > .matchup").forEach(matchup => {
            const allBlank = Array.from(matchup.querySelectorAll(".team")).every(t => t.classList.contains("team-placeholder"));
            if (allBlank) return;
            if (!matchup.querySelector(".team.selected")) {
                missing.push(`Final Four — ${id === "ff_left" ? "Left Semifinal" : "Right Semifinal"}`);
            }
        });
    });

    // Championship
    const champContainer = document.getElementById("championship");
    if (champContainer) {
        champContainer.querySelectorAll(":scope > .matchup").forEach(matchup => {
            const allBlank = Array.from(matchup.querySelectorAll(".team")).every(t => t.classList.contains("team-placeholder"));
            if (allBlank) return;
            if (!matchup.querySelector(".team.selected")) {
                missing.push("Championship Game");
            }
        });
    }

    // Champion display
    const champDiv = document.getElementById("champion");
    if (champDiv && !champDiv.innerText.trim()) {
        missing.push("National Champion");
    }

    return { valid: missing.length === 0, missing };
}

/* =========================================================
   BUILD JSON FOR SUBMISSION
   Saves full matchup pairs (both teams) for correct display when viewing brackets.
   Skips placeholder-only matchups so incomplete rounds aren't saved as blank data.
   ========================================================= */
function buildBracketJSON() {
    const result = {};
    document.querySelectorAll(".matchups").forEach(roundElem => {
        const id = roundElem.id;
        if (!id) return;
        const pairs = [];
        roundElem.querySelectorAll(".matchup").forEach(m => {
            const teams = m.querySelectorAll(".team");
            const t1 = teams[0], t2 = teams[1];
            if (t1 && t2) {
                const n1 = t1.getAttribute("data-name") || "";
                const n2 = t2.getAttribute("data-name") || "";
                // Skip matchups where both slots are still placeholders
                if (!n1 && !n2) return;
                pairs.push(
                    { seed: t1.getAttribute("data-seed") || "", name: n1 },
                    { seed: t2.getAttribute("data-seed") || "", name: n2 }
                );
            }
        });
        result[id] = pairs;
    });
    const champDiv = document.getElementById("champion");
    result["champion"] = champDiv ? champDiv.innerText.trim() : null;
    return result;
}
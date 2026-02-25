/* =========================================================
   TEAM ROW TEMPLATE
   ========================================================= */
function createTeamRow(seed, name, isSelected, isEliminated) {
    let cls = "team";
    if (isSelected)   cls += " selected";
    if (isEliminated) cls += " eliminated";
    return `<div class="${cls}" data-seed="${seed}" data-name="${name}">
                <span class="seed">${seed}</span>
                <span class="team-name">${name}</span>
            </div>`;
}

/* =========================================================
   LOAD INITIAL ROUND OF 64 TEAMS
   ========================================================= */
function loadInitialTeams(teamsData) {
    console.log("Loading initial bracket teams...");
    ["west", "south", "east", "midwest"].forEach(region => {
        const teams  = teamsData[region] || [];
        const target = document.getElementById(`${region}_r64`);
        if (!target) { console.warn("Missing:", `${region}_r64`); return; }
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
   Clones each .team element to prevent stacking listeners.
   ========================================================= */
function attachClickHandlers() {
    document.querySelectorAll(".team").forEach(oldTeam => {
        const newTeam = oldTeam.cloneNode(true);
        oldTeam.parentNode.replaceChild(newTeam, oldTeam);
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
   ADVANCE WINNER TO NEXT ROUND
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
    if (!nextContainer) { console.warn("Missing container:", nextContainerId); return; }

    let matchups = nextContainer.querySelectorAll(":scope > .matchup");
    while (matchups.length <= slotIndex) {
        const div = document.createElement("div");
        div.className = "matchup";
        nextContainer.appendChild(div);
        matchups = nextContainer.querySelectorAll(":scope > .matchup");
    }

    const targetMatchup = matchups[slotIndex];

    const newTeamEl = document.createElement("div");
    newTeamEl.className = "team";
    newTeamEl.setAttribute("data-seed", teamObj.seed);
    newTeamEl.setAttribute("data-name", teamObj.name);
    newTeamEl.innerHTML = `<span class="seed">${teamObj.seed}</span>
                           <span class="team-name">${teamObj.name}</span>`;

    const existingTeams = targetMatchup.querySelectorAll(":scope > .team");

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
   Populates all rounds from server data and highlights
   winners (teams that appear in the following round).
   ========================================================= */
function autofillBracket(data) {
    const roundOrder = [
        ["west_r64",  "west_r32"],
        ["west_r32",  "west_s16"],
        ["west_s16",  "west_e8"],
        ["west_e8",   "ff_left"],
        ["south_r64", "south_r32"],
        ["south_r32", "south_s16"],
        ["south_s16", "south_e8"],
        ["south_e8",  "ff_left"],
        ["east_r64",  "east_r32"],
        ["east_r32",  "east_s16"],
        ["east_s16",  "east_e8"],
        ["east_e8",   "ff_right"],
        ["midwest_r64", "midwest_r32"],
        ["midwest_r32", "midwest_s16"],
        ["midwest_s16", "midwest_e8"],
        ["midwest_e8",  "ff_right"],
        ["ff_left",     "championship"],
        ["ff_right",    "championship"],
        ["championship", "__champion__"],
    ];

    // Clear everything
    const allContainerIds = [
        "west_r64","west_r32","west_s16","west_e8",
        "south_r64","south_r32","south_s16","south_e8",
        "east_r64","east_r32","east_s16","east_e8",
        "midwest_r64","midwest_r32","midwest_s16","midwest_e8",
        "ff_left","ff_right","championship"
    ];
    allContainerIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = "";
    });
    const champDiv = document.getElementById("champion");
    if (champDiv) champDiv.innerText = "";

    // Build a set of winner names per container for fast lookup.
    // A team is a "winner" in container X if it appears in the next round's container.
    // We collect all names that appear in the NEXT container's team list.
    function getWinnerNames(currentId, nextId) {
        const winners = new Set();
        if (nextId === "__champion__") {
            if (data.champion) winners.add(data.champion);
            return winners;
        }
        const nextTeams = data[nextId] || [];
        nextTeams.forEach(t => winners.add(t.name));
        return winners;
    }

    // Special case: ff_left and ff_right both feed into championship,
    // but the server splits them. We build winner sets per source container.
    // For e8→ff: the winner from west_e8 is the first team in ff_left,
    // winner from south_e8 is the second team in ff_left, etc.
    // The getWinnerNames approach (any name in the next container) works fine
    // because each e8 produces only 1 winner and they're distinct teams.

    // Render each container with selected/eliminated classes
    allContainerIds.forEach(containerId => {
        const teams = data[containerId];
        if (!teams || teams.length === 0) return;

        const container = document.getElementById(containerId);
        if (!container) return;

        // Find what the "next" container is for this one
        // (there may be two entries in roundOrder for the same containerId — e.g. ff_left)
        const nextIds = roundOrder
            .filter(([cur]) => cur === containerId)
            .map(([, nxt]) => nxt);

        // Collect all winner names from all possible next containers
        const winnerNames = new Set();
        nextIds.forEach(nextId => {
            getWinnerNames(containerId, nextId).forEach(n => winnerNames.add(n));
        });

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

    // Set champion display
    if (data.champion && champDiv) {
        champDiv.innerText = data.champion;
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
        const picks = [];
        roundElem.querySelectorAll(".matchup").forEach(m => {
            const sel = m.querySelector(".team.selected");
            picks.push(sel ? sel.getAttribute("data-name") : null);
        });
        result[id] = picks;
    });
    const champDiv = document.getElementById("champion");
    result["champion"] = champDiv ? champDiv.innerText.trim() : null;
    return result;
}

console.log("Bracket JS loaded.");
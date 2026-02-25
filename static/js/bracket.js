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

/*
 * Returns { nextContainerId, slotIndex, teamSlot }
 *
 * slotIndex = which .matchup div inside the next container
 * teamSlot  = 0 (top/first team) or 1 (bottom/second team)
 *
 * KEY LOGIC FOR FINAL FOUR:
 *   ff_left  holds TWO matchups: slot 0 = West winner, slot 1 = South winner
 *   ff_right holds TWO matchups: slot 0 = East winner, slot 1 = Midwest winner
 *   Then ff_left's ONE game winner + ff_right's ONE game winner → championship
 *
 *   Wait — that's wrong for a real bracket. The correct structure is:
 *   ff_left  = ONE matchup: West winner (top) vs South winner (bottom)
 *   ff_right = ONE matchup: East winner (top) vs Midwest winner (bottom)
 *   championship = ONE matchup: ff_left winner (top) vs ff_right winner (bottom)
 *
 *   So West  → ff_left  slotIndex=0, teamSlot=0
 *      South → ff_left  slotIndex=0, teamSlot=1
 *      East  → ff_right slotIndex=0, teamSlot=0
 *      Midwest→ ff_right slotIndex=0, teamSlot=1
 */
function getNextSlot(matchupElem) {
    const containerId = getContainerId(matchupElem);
    const region      = getRegion(matchupElem);
    const round       = getRound(matchupElem);

    const container   = matchupElem.closest(".matchups");
    const allMatchups = Array.from(container.querySelectorAll(":scope > .matchup"));
    const matchupIdx  = allMatchups.indexOf(matchupElem);

    const regionRounds = ["r64", "r32", "s16", "e8"];
    const roundIdx     = regionRounds.indexOf(round);

    // Inside a region: pairs of matchups collapse into one next-round matchup
    if (roundIdx !== -1 && roundIdx < regionRounds.length - 1) {
        return {
            nextContainerId: `${region}_${regionRounds[roundIdx + 1]}`,
            slotIndex:       Math.floor(matchupIdx / 2),
            teamSlot:        matchupIdx % 2
        };
    }

    // Elite 8 → Final Four (one matchup per ff container)
    if (round === "e8") {
        if (region === "west")    return { nextContainerId: "ff_left",  slotIndex: 0, teamSlot: 0 };
        if (region === "south")   return { nextContainerId: "ff_left",  slotIndex: 0, teamSlot: 1 };
        if (region === "east")    return { nextContainerId: "ff_right", slotIndex: 0, teamSlot: 0 };
        if (region === "midwest") return { nextContainerId: "ff_right", slotIndex: 0, teamSlot: 1 };
    }

    // Final Four → Championship
    if (round === "left")  return { nextContainerId: "championship", slotIndex: 0, teamSlot: 0 };
    if (round === "right") return { nextContainerId: "championship", slotIndex: 0, teamSlot: 1 };

    // Championship → Champion display
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

    // Champion display is a plain div, not a .matchups container
    if (nextContainerId === "champion_display") {
        const el = document.getElementById("champion");
        if (el) el.innerText = `${teamObj.seed} ${teamObj.name}`;
        return;
    }

    const nextContainer = document.getElementById(nextContainerId);
    if (!nextContainer) { console.warn("Missing container:", nextContainerId); return; }

    // Ensure enough matchup divs exist in the next container
    let matchups = nextContainer.querySelectorAll(":scope > .matchup");
    while (matchups.length <= slotIndex) {
        const div = document.createElement("div");
        div.className = "matchup";
        nextContainer.appendChild(div);
        matchups = nextContainer.querySelectorAll(":scope > .matchup");
    }

    const targetMatchup = matchups[slotIndex];

    // Build new team element
    const newTeamEl = document.createElement("div");
    newTeamEl.className = "team";
    newTeamEl.setAttribute("data-seed", teamObj.seed);
    newTeamEl.setAttribute("data-name", teamObj.name);
    newTeamEl.innerHTML = `<span class="seed">${teamObj.seed}</span>
                           <span class="team-name">${teamObj.name}</span>`;

    // Place in the correct slot (0=top, 1=bottom), replacing if already filled
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
        
        // Determine winners for this container
        const nextIds = roundOrder.filter(([cur]) => cur === containerId).map(([, nxt]) => nxt);
        const winnerNames = new Set();
        nextIds.forEach(nextId => {
            const nextTeams = data[nextId] || [];
            nextTeams.forEach(t => winnerNames.add(t.name));
        });
        const container = document.getElementById(containerId);
        if (!container) return;
        for (let i = 0; i + 1 < teams.length; i += 2) {
            const t1 = teams[i];
            const t2 = teams[i + 1];
            const t1wins = winnerNames.has(t1.name);
            const t2wins = winnerNames.has(t2.name);
            const div = document.createElement("div");
            div.className = "matchup";
            div.innerHTML = createTeamRow(t1.seed, t1.name)
                          + createTeamRow(t2.seed, t2.name);
            div.innerHTML = createTeamRow(t1.seed, t1.name, t1wins, !t1wins && t2wins)
                          + createTeamRow(t2.seed, t2.name, t2wins, !t2wins && t1wins);
            container.appendChild(div);
        }
    });

    if (data.champion && champDiv) champDiv.innerText = data.champion;

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
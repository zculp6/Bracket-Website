/* =========================================================
   TEAM ROW TEMPLATE
   ========================================================= */
function createTeamRow(seed, name, isSelected = false, isEliminated = false) {
    let cls = "team";
    if (isSelected)   cls += " selected";
    if (isEliminated) cls += " eliminated";
    return `<div class="${cls}" data-seed="${seed}" data-name="${name}">
                <span class="seed">${seed}</span>
                <span class="team-name">${name}</span>
            </div>`;
}

/* =========================================================
   ATTACH CLICK HANDLERS TO UNBOUND TEAMS
   ========================================================= */
function attachHandlersToUnbound() {
    document.querySelectorAll(".team:not([data-bound])").forEach(team => {
        team.dataset.bound = "true";
        team.addEventListener("click", function () {
            const matchup = this.closest(".matchup");
            if (!matchup) return;

            // Clear previous selections in this matchup
            matchup.querySelectorAll(".team").forEach(t => {
                t.classList.remove("selected", "eliminated");
            });

            // Mark clicked team as selected, others eliminated
            this.classList.add("selected");
            matchup.querySelectorAll(".team:not(.selected)").forEach(t => {
                t.classList.add("eliminated");
            });

            // Advance the winner
            advanceTeam(matchup, {
                seed: this.getAttribute("data-seed"),
                name: this.getAttribute("data-name")
            });
        });
    });
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
    attachHandlersToUnbound();
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
        if (existingTeams[0]) targetMatchup.replaceChild(newTeamEl, existingTeams[0]);
        else targetMatchup.insertBefore(newTeamEl, targetMatchup.firstChild);
    } else {
        if (existingTeams[1]) targetMatchup.replaceChild(newTeamEl, existingTeams[1]);
        else targetMatchup.appendChild(newTeamEl);
    }

    attachHandlersToUnbound(); // attach only to the newly added team
}

/* =========================================================
   AUTOFILL BRACKET FROM SERVER DATA
   ========================================================= */
function autofillBracket(data) {
    const allContainerIds = [
        "west_r64","west_r32","west_s16","west_e8",
        "south_r64","south_r32","south_s16","south_e8",
        "east_r64","east_r32","east_s16","east_e8",
        "midwest_r64","midwest_r32","midwest_s16","midwest_e8",
        "ff_left","ff_right","championship"
    ];

    // Clear everything first
    allContainerIds.forEach(id => {
        const el = document.getElementById(id);
        if (el) el.innerHTML = "";
    });
    const champDiv = document.getElementById("champion");
    if (champDiv) champDiv.innerText = "";

    // Render teams per container
    allContainerIds.forEach(containerId => {
        const teams = data[containerId];
        if (!teams || teams.length === 0) return;
        const container = document.getElementById(containerId);
        if (!container) return;

        for (let i = 0; i + 1 < teams.length; i += 2) {
            const t1 = teams[i];
            const t2 = teams[i + 1];
            const div = document.createElement("div");
            div.className = "matchup";
            div.innerHTML = createTeamRow(t1.seed, t1.name)
                          + createTeamRow(t2.seed, t2.name);
            container.appendChild(div);
        }
    });

    // Set champion
    if (data.champion && champDiv) {
        champDiv.innerText = data.champion;
    }

    attachHandlersToUnbound();
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
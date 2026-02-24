/* =========================================================
   GLOBAL BRACKET STATE
   ========================================================= */

let bracket = {
    west: {
        r64: [],
        r32: [],
        s16: [],
        e8: []
    },
    south: {
        r64: [],
        r32: [],
        s16: [],
        e8: []
    },
    east: {
        r64: [],
        r32: [],
        s16: [],
        e8: []
    },
    midwest: {
        r64: [],
        r32: [],
        s16: [],
        e8: []
    },
    final_four: {
        left: [],
        right: []
    },
    championship: [],
    champion: null
};

/* =========================================================
   TEAM TEMPLATE FOR MATCHUPS
   ========================================================= */
function createTeamRow(seed, name) {
    return `
        <div class="team" data-seed="${seed}" data-name="${name}">
            <span class="seed">${seed}</span>
            <span class="team-name">${name}</span>
        </div>
    `;
}

/* =========================================================
   DISPLAY ROUND OF 64 TEAMS
   ========================================================= */
function loadInitialTeams(teamsData) {
    console.log("Loading initial bracket teams...");

    Object.keys(teamsData).forEach(region => {
        let teams = teamsData[region];
        let target = document.getElementById(`${region}_r64`);

        target.innerHTML = "";

        for (let i = 0; i < teams.length; i += 2) {
            let matchup = `
                <div class="matchup">
                    ${createTeamRow(teams[i].seed, teams[i].name)}
                    ${createTeamRow(teams[i+1].seed, teams[i+1].name)}
                </div>
            `;
            target.innerHTML += matchup;
        }
    });

    attachClickHandlers();
}

/* =========================================================
   ATTACH CLICK HANDLERS TO TEAMS
   ========================================================= */
function attachClickHandlers() {

    document.querySelectorAll(".team").forEach(team => {

        team.addEventListener("click", function () {

            let parentMatchup = this.parentElement;
            let teams = parentMatchup.querySelectorAll(".team");

            // Remove previous selection
            teams.forEach(t => t.classList.remove("selected"));

            // Select clicked team
            this.classList.add("selected");

            // Advance winner
            let seed = this.getAttribute("data-seed");
            let name = this.getAttribute("data-name");

            advanceTeam(parentMatchup, {
                seed: seed,
                name: name
            });
        });
    });
}

/* =========================================================
   ADVANCING WINNERS THROUGH ROUNDS
   ========================================================= */
function advanceTeam(matchupElem, teamObj) {

    let region = findRegionFromElement(matchupElem);
    let round = findRoundFromElement(matchupElem);

    let nextRoundId = getNextRoundId(region, round);

    if (!nextRoundId) {
        console.log("Reached final round for region:", region);
        return;
    }

    let container = document.getElementById(nextRoundId);

    // Find first open matchup area for next round
    let matchups = container.querySelectorAll(".matchup");
    let target = null;

    matchups.forEach(m => {
        let teams = m.querySelectorAll(".team");
        if (teams.length < 2) {
            target = m;
        }
    });

    // If no partially filled matchup exists, create a new one
    if (!target) {
        let m = document.createElement("div");
        m.className = "matchup";
        m.innerHTML = createTeamRow(teamObj.seed, teamObj.name);
        container.appendChild(m);
        attachClickHandlers();
        return;
    }

    // Add the winner to this matchup
    target.innerHTML += createTeamRow(teamObj.seed, teamObj.name);
    attachClickHandlers();

    // If this fills the matchup, the user will be able to click again to advance
}

/* =========================================================
   UTIL HELPERS
   ========================================================= */

function findRegionFromElement(elem) {
    let id = elem.parentElement.id;
    return id.split("_")[0];  // west_r64 → "west"
}

function findRoundFromElement(elem) {
    let id = elem.parentElement.id;
    return id.split("_")[1];  // west_r64 → "r64"
}

function getNextRoundId(region, round) {
    const order = ["r64", "r32", "s16", "e8"];

    let idx = order.indexOf(round);

    // Region sends to Final Four if next == e8
    if (round === "e8") {
        if (region === "west" || region === "south") return "ff_left";
        if (region === "east" || region === "midwest") return "ff_right";
    }

    if (idx === -1 || idx === order.length - 1) return null;

    return `${region}_${order[idx + 1]}`;
}

/* =========================================================
   AUTOFILL BRACKET
   ========================================================= */
function autofillBracket(data) {

    const round1 = data.round_1;

    const teamsData = {
        west: round1.slice(0, 16),        // 8 matchups
        south: round1.slice(16, 32),
        east: round1.slice(32, 48),
        midwest: round1.slice(48, 64)
    };

    // Load teams into Round 64 regions
    Object.keys(teamsData).forEach(region => {
        let teams = teamsData[region];
        let target = document.getElementById(`${region}_r64`);
        target.innerHTML = "";

        for (let i = 0; i < teams.length; i += 2) {
            let m = `
                <div class="matchup">
                    ${createTeamRow(teams[i].seed, teams[i].name)}
                    ${createTeamRow(teams[i+1].seed, teams[i+1].name)}
                </div>
            `;
            target.innerHTML += m;
        }
    });

    attachClickHandlers();
}

/* =========================================================
   BUILD JSON FOR SUBMISSION
   ========================================================= */
function buildBracketJSON() {

    let result = {};

    document.querySelectorAll(".matchups").forEach(roundElem => {
        let id = roundElem.id;
        let matchups = [];

        roundElem.querySelectorAll(".matchup").forEach(m => {
            let teams = m.querySelectorAll(".team.selected");
            if (teams.length === 1) {
                matchups.push(teams[0].getAttribute("data-name"));
            } else {
                matchups.push(null);
            }
        });

        result[id] = matchups;
    });

    // Champion
    let champ = document.getElementById("champion").innerText;
    result["champion"] = champ;

    return result;
}

console.log("Bracket JS loaded.");
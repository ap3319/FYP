var loadingModal = new bootstrap.Modal(document.getElementById("loading-modal"))



function updateTurnIndicator(gameData){

   

    if (gameData.winner == "1"){
        document.getElementById("turn").textContent = "You Won!"
        document.getElementById("turn-indicator").className = "alert alert-primary"
    }
    else if (gameData.winner == "2"){
        document.getElementById("turn").textContent = "Robot Won!"
        document.getElementById("turn-indicator").className = "alert alert-info"
    }
    else if (gameData.winner == "0"){
        document.getElementById("turn").textContent = "Draw!"
        document.getElementById("turn-indicator").className = "alert alert-dark"
    }

    else if (!gameData.game_on){
            document.getElementById("turn").textContent = ""
            document.getElementById("turn-indicator").className = "alert alert-secondary"
        }  


    else if (gameData.turn == "1"){
        document.getElementById("turn").textContent = "Your Turn"
        document.getElementById("turn-indicator").className = "alert bg-warning"
    }
    else if (gameData.turn == "2"){
        document.getElementById("turn").textContent = "Robot's Turn, please wait for me!"
        document.getElementById("turn-indicator").className = "alert bg-danger"
    }
}



function updateError(gameData){

    if (gameData.error != ""){
        document.getElementById("error").className = "alert alert-danger"
        document.getElementById("error").textContent = gameData.error
    }
    else{
        document.getElementById("error").className = "alert alert-danger invisible"
    }
   
}


function updateChart(scores){

    if (scores){
        scoreChart.data.datasets[0].data = scores

        const red ="rgba(255 ,99 ,132 ,0.5)"
        const blue = "rgba(54, 162, 235, 0.5)"
        const colours = [blue,blue,blue,blue,blue,blue,blue]

        let bestScore = -100000
        let idx = 0
        for (let i = 0; i < scores.length; i++) {
            if ((scores[i] != null) && (scores[i] > bestScore) ){
                bestScore = scores[i]
                idx = i
            }
            
        }
        
        colours [idx ] = red
        scoreChart.data.datasets[0].backgroundColor = colours
        scoreChart.update()

        }
}



function updateHumanBoard(board){

    if (board){
        for (let row = 0; row <6; row++) {

            for (let col = 0; col <7; col++) {
                const disc = board[row][col]
                const cell = cells[row*7 +col]
                
                if (disc ==1){
                    cell.className = "cell bg-warning"

                }
                else if (disc ==2){
                    cell.className = "cell bg-danger"

                }
                else if (disc ==0){
                    cell.className = "cell bg-white"

                }

            }
        }
            
     }  

}









//flask runs functions via url then we update status text
async function postUrlUpdateState(url) {
    //await so js contuinues running whilst waiting for response
    const response = await fetch(url,{  method: "POST"});
    if(!response.ok)
    {// catches 404s, 404 doesnt reject promise
      throw new Error(`Response status: ${response.status}`);
    }

    const text = await response.text();//reads body of response ALSO needs await
    
    document.getElementById("state").textContent = text;

}


async function checkBoard (){ //board state from game state.py via game loop

    const gameResponse = await fetch("/game_data", {method: "GET"});
    const gameData = await gameResponse.json()

    updateTurnIndicator(gameData)

    updateError(gameData)

    if (gameData["loading-message"]){
            
        document.getElementById("loading-message").textContent = gameData["loading-message"]
        loadingModal.show()
        }

    else{
        loadingModal.hide()
    }
    
    //for what column robot dropped in
    document.getElementById("little-message").textContent = gameData["little-message"]

    const scores =  gameData["scores"]
    updateChart(scores)

    updateHumanBoard(gameData["board"])

}

async function checkState(){ //state from robot state machine
    const statusResponse = await fetch("/status", {method: "GET"});
    const text = await statusResponse.text()

    //update on off chance game loop crashes, as would go to IDLE
    document.getElementById("state").textContent = text;
}


async function abandonGameMessage(){ //state from robot state machine
    document.getElementById("little-message").textContent = "Game abandoned, new game started."

}



//buttons 
const start_btn = document.getElementById("button-start-game" );
start_btn.addEventListener("click", function() {postUrlUpdateState("/start")} );

const abandon_btn = document.getElementById("button-abandon-game" );
abandon_btn.addEventListener("click", function() { postUrlUpdateState("/abandon_game"); abandonGameMessage()} );

const reset_btn = document.getElementById("button-reset");
reset_btn.addEventListener("click", function() { postUrlUpdateState("/reset")} );

const estop_btn = document.getElementById("button-estop");
estop_btn.addEventListener("click", function() { postUrlUpdateState("/estop")} );

const difficulty = document.getElementById("difficulty-select");
difficulty.addEventListener("change", function() { postUrlUpdateState("/set_difficulty/" + this.value)} );



// drawing human board, honestly idk if this should be removed but its done so...
const cells = []
for (let row = 0; row <6; row++) {

  for (let col = 0; col <7; col++) {
    const cell = document.createElement("div")
    cell.className = "cell empty";
    document.getElementById("board").appendChild(cell); 

    cells[row * 7 + col] =cell;

  }
    
}


function pollStateAndGame()
    {
        checkState()
        checkBoard ()
    }


setInterval(pollStateAndGame,1000)






































//notes:
//Feature		    let             	const
///Scope		    Block-scope { }	    Block-scope { }
// Reassignment		Can be updated	Cannot be updated
//https://www.w3schools.com/js/js_let.asp

//https://www.w3schools.com/js/js_api_fetch.asp
//https://www.w3schools.com/js/js_async_fetch.asp

//addeventlistener calls second arg which is a function on the first, 
//if want to do something elsee need to call function with no arg
// that then calls another function with the right argument 

//https://developer.mozilla.org/en-US/docs/Web/API/Fetch_API/Using_Fetch#reading_the_response_body
// fetch returns a promise (three states pending, fulfilled, rejected)
// await needs async else pauses until promise fulfilled
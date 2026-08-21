// robot's scores for each column from its last turn
// col6 leftmost because the human faces the robot. 
//https://www.chartjs.org/docs/latest/samples/bar/vertical.html

const red ="rgba(255 ,99 ,132 ,0.5)"
const blue = "rgba(54, 162, 235, 0.5)"

const labels = ["Column 6","Column 5", "Column 4", "Column 3", "Column 2", "Column 1", "Column 0"];
const scores = [0,0,0,0,0,0,0];

const data = {
  labels: labels,
  datasets: [
    {
      label: "Robot's score per column",
      data: scores,
      //must start as full 7 columns so can colour each one seperately
      backgroundColor: [blue,blue,blue,blue,blue,blue,blue],
      borderWidth: 0,
      borderRadius: 5,
      borderSkipped: false,
    }
    
  ]
};


const config = {
  type: 'bar',
  data: data,
  options: {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,

    scales: {
      y: {min: -20, max: 20} //to stop resizing
    },

    plugins: {
      legend: {
        display: false,
        position: 'top',
      },

      title: {
        display: true,
        text: 'solver score of each column on robots last turn, higher = better for robot'
      }
    }
  },
};


//new for a new object
const scoreChart =  new Chart(document.getElementById('scoreChart'), config);

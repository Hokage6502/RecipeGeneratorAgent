const express = require('express');
const path = require('path');
const { spawn } = require('child_process'); // Import the child_process module

const app = express();
const PORT = 3000;

// Middleware to parse form data
app.use(express.urlencoded({ extended: true }));


// Serve the HTML form from the `frontend` directory
app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, '../frontend/form.html'));
});

// Handle form submissions
app.post('/submit', (req, res) => {
    const { diet, cuisine, ingredients } = req.body;

    // Prepare the specific ingredients by splitting the string
    const specificIngredients = ingredients.split(',').map(item => item.trim());

    // Spawn the Python process with arguments
    const pythonProcess = spawn('python', [
        'agent.py',           // The Python script
        diet,                 // Diet (as a command-line argument)
        cuisine,              // Cuisine (as a command-line argument)
        specificIngredients.join(",")  // Ingredients (joined as a comma-separated string)
    ]);

    // Collect the output (recipe) from Python
    let pythonOutput = '';
    pythonProcess.stdout.on('data', (data) => {
        pythonOutput += data.toString();
    });

    pythonProcess.stderr.on('data', (error) => {
        console.error(`Error from Python script: ${error.toString()}`);
    });

    pythonProcess.on('close', (code) => {
        console.log(`Python script exited with code ${code}`);
        res.send(`<h1>Generated Recipe</h1><pre>${pythonOutput}</pre>`);
    });
});

// Start the server
app.listen(PORT, () => {
    console.log(`Server running at http://localhost:${PORT}`);
});


// const express = require('express');
// const path = require('path');
// const { spawn } = require('child_process'); // Import the child_process module

// const app = express();
// const PORT = 3000;

// // Middleware to parse form data
// app.use(express.urlencoded({ extended: true }));

// // Serve the HTML form from the `frontend` directory
// app.get('/', (req, res) => {
//     res.sendFile(path.join(__dirname, '../frontend/form.html'));
// });

// // Handle form submissions
// app.post('/submit', (req, res) => {
//     const { diet, cuisine, ingredients } = req.body;

//     // Prepare the specific ingredients by splitting the string
//     const specificIngredients = ingredients.split(',').map(item => item.trim());

//     // // Spawn the Python process with arguments
//     // const pythonProcess = spawn('python', [
//     //     'agent.py',           // The Python script
//     //     diet,                 // Diet (as a command-line argument)
//     //     cuisine,              // Cuisine (as a command-line argument)
//     //     specificIngredients.join(",")  // Ingredients (joined as a comma-separated string)
//     // ]);

//     // Prepare data for Python script
//     // const inputData = JSON.stringify({ 
//     //     diet, 
//     //     cuisine, 
//     //     specific_ingredients: ingredients.split(',').map(item => item.trim())
//     // });

//     // Spawn the Python process
//     const pythonProcess = spawn('python', ['agent.py', diet, cuisine, specificIngredients]);

//     // Send user inputs to the Python script
//     // pythonProcess.stdin.write(inputData);
//     // pythonProcess.stdin.end();

//     // Collect the output (recipe) from Python
//     let pythonOutput = '';
//     pythonProcess.stdout.on('data', (data) => {
//         pythonOutput += data.toString();
//     });

//     pythonProcess.stderr.on('data', (error) => {
//         console.error(`Error from Python script: ${error.toString()}`);
//     });

//     pythonProcess.on('close', (code) => {
//         console.log(`Python script exited with code ${code}`);
//         res.send(`<h1>Generated Recipe</h1><pre>${pythonOutput}</pre>`);
//     });
// });

// // Start the server
// app.listen(PORT, () => {
//     console.log(`Server running at http://localhost:${PORT}`);
// });

## Run the Code yourself

You can now train the net by running

`th train.lua -csv_file bounce.csv`

The parameters (network size, amount of layers etc.) can be set within the code. The code will write
state files of the network's state every 200 iterations. In order to sample from the model, simply do

`th sample.lua -state_file epoch24loss0.01362422014985.net -input_dimension 8 -length 1000 > out.csv`

This is going to write a csv file of 1000 generated vectors of size 8 (this has to be the size the 
network has actually been trained with). 
Enjoy the ride!


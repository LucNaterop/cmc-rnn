require 'rnn'
require 'CSV.lua'
require 'optim'

local X = CSV.read('Symbol.csv')     -- training data

-- hyper-parameters 
 batchSize = 1
 rho =50 -- sequence length
 hiddenSize = 100
 inputDimension = X:size(2)
 lr = 0.05
 maxIt = 500
 flag=0

print(string.format("InputDimension %d ; InputSize = %d ", inputDimension, X:size(1)))

if flag==1 then
   -- load the model (importand to reinitialise the model or give a different model-name)
   rnn = torch.load('flag_rnn1.net')
else

   -- build simple recurrent neural network

   rnn = nn.Sequential()
      :add(nn.LSTM(inputDimension,hiddenSize,rho))
      :add(nn.LSTM(hiddenSize,hiddenSize,rho))
      :add(nn.Linear(hiddenSize, inputDimension))

   -- wrap the non-recurrent module (Sequential) in Recursor.
   -- This makes it a recurrent module
   -- i.e. Recursor is an AbstractRecurrent instance
   rnn = nn.Recursor(rnn, rho)
   print(rnn)
end

 local params, grads = rnn:getParameters()
 criterion = nn.MSECriterion()
 --criterion.sizeAverage = false --throws the normalisation (1/n) away (faster)

 local  p = 1 -- data pointer
 local smothloss=100
 local epoch=1


-- function für optim
local feval = function(x)
  if x ~= params then
    params:copy(x)
  end
  grads:zero()
  local loss=0
  local inputs, targets, outputs = {}, {}, {}
  
  -- forward
   for step=1,rho do
      inputs[step] = X[p+step-1]
      targets[step] = X[p+step]
      
      --ouput normal:
      --outputs[step] = rnn:forward(inputs[step])
      
      --Idee negative Amplitude-->0: (seems to converge faster!) 
        out = rnn:forward(inputs[step])
        idx=torch.lt(out, 0) --überall eins, falls kleiner als null, sonst null
        out[idx]=0 --überall wo idx==1 wird out zu null, sonst unverändert
        outputs[step]=out

      loss = loss + criterion:forward(outputs[step],targets[step])
   end
  
  -- backward
  local gradOutputs, gradInputs = {}, {}
  for step=rho,1,-1 do -- reverse order of forward calls
     gradOutputs[step] = criterion:backward(outputs[step], targets[step])
     gradInputs[step] = rnn:backward(inputs[step], gradOutputs[step])--unnecessary save of gradInputs
  end
  return loss, grads
end

------------------------------------------------------------------------
-- optimization loop (with optim)
local optim_state = {lr}
for i = 1, maxIt do
   if(p+rho > X:size(1)) then
        p = 1
        epoch=epoch+1
   end
   
  local _, loss = optim.adagrad(feval, params, optim_state)
  smothloss=0.95*smothloss+0.05*loss[1]

  if i % 10 == 0 then
      print(string.format("Iteration %d ; Smothloss = %f ; Epoch %d ", i, smothloss,epoch))
  end
  p = p+rho
end



--WITHOUT OPTIM
--iteration = 1
--while true do
--   if(p+rho > X:size(1)) then
--      p = 1
--      epoch=epoch+1
--   end
--   local inputs, targets = {}, {} 
--   for step=1,rho do
--      inputs[step] = X[p+step-1]
--      targets[step] = X[p+step]
--   end
--   p = p+rho
--
--   -- 2. forward sequence through rnn
--   
--   rnn:zeroGradParameters() 
--   rnn:forget() -- forget all past time-steps
--   local outputs, err = {}, 0
--   for step=1,rho do
--      --Idee normal:
--      --outputs[step] = rnn:forward(inputs[step])
--
--      --Idee negative Amplitude-->0:
--      out = rnn:forward(inputs[step])
--      idx=torch.lt(out, 0) --überall eins, falls kleiner als null, sonst null
--      out[idx]=0 --überall wo idx==1 wird out zu null, sonst unverändert
--      outputs[step]=out
--
--
--
--      err = err + criterion:forward(outputs[step],targets[step])
--      --err = err + torch.abs(outputs[step]-targets[step])+
--
--   end
--   smothloss=0.95*smothloss+0.05*err
--   if iteration%10==0 then
--      print(string.format("Iteration %d ; Smothloss = %f ; Epoche %d ", iteration, smothloss,epoch))
--   end
--
--   -- 3. backward sequence through rnn (i.e. backprop through time)
--   
--   local gradOutputs, gradInputs = {}, {}
--   for step=rho,1,-1 do -- reverse order of forward calls
--      gradOutputs[step] = criterion:backward(outputs[step], targets[step])
--      gradInputs[step] = rnn:backward(inputs[step], gradOutputs[step])
--   end
--
--   -- 4. update
--   
--   rnn:updateParameters(lr)
--   
--   iteration = iteration + 1
--
--   if( iteration >= maxIt) then
--      break
--   end
--
--end

-- save the model
torch.save('flag_rnn1.net', rnn)


function sample(seed, N)
   local samples = torch.zeros(N, inputDimension)
   samples[1] = rnn:forward(seed)
   for i=2,N do
      samples[i] = rnn:forward(samples[i-1])
   end
   return samples
end

--local seed = torch.rand(inputDimension) -- X[1]
local seed = X[p]
local samples = sample(seed, 400)
-- print(samples)
CSV.write(samples,'samples')

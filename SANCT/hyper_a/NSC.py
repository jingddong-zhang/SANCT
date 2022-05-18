import torch
import torch.nn.functional as F
import numpy as np
import timeit
import argparse
from hessian import hessian
from hessian import jacobian
from functions import *
parser = argparse.ArgumentParser('ODE demo')
parser.add_argument('--N', type=float, default=3000)
parser.add_argument('--num', type=float, default=4)
parser.add_argument('--lr', type=float, default=0.05)
parser.add_argument('--niters', type=int, default=1)
parser.add_argument('--batch_size', type=int, default=3000)
args = parser.parse_args()

def setup_seed(seed):
    torch.manual_seed(seed)
    np.random.seed(seed)

setup_seed(10)

class ControlNet(torch.nn.Module):
    def __init__(self, n_input, n_hidden, n_output):
        super(ControlNet, self).__init__()
        torch.manual_seed(2)
        self.layer1 = torch.nn.Linear(n_input, n_hidden)
        self.layer2 = torch.nn.Linear(n_hidden, n_hidden)
        self.layer3 = torch.nn.Linear(n_hidden, n_output)

    def forward(self, data):
        sigmoid = torch.nn.ReLU()
        h_1 = sigmoid(self.layer1(data))
        h_2 = sigmoid(self.layer2(h_1))
        out = self.layer3(h_2)
        x = data[:,0:2]
        return out*x


def get_batch(data):
    s=torch.from_numpy(np.random.choice(np.arange(args.N,dtype=np.int64),args.batch_size,replace=False))
    batch_x=data[s,:]  # (M, D)
    return batch_x

def f_(data,u=0):
    x,y = data[:,0:2],data[:,2:4]
    z = torch.zeros_like(x)
    G=9.81  # gravity
    L=0.5  # length of the pole
    m=0.15  # ball mass
    b=0.1  # friction
    for i in range(len(x)):
        w,v = x[i,:]
        z[i,:] = torch.tensor([v, G*np.sin(w)/L +(-b*v)/(m*L**2)])#+u[i]
    return z

def g_(data,u):
    x,y = data[:,0:2],data[:,2:4]
    z = torch.zeros_like(x)
    for i in range(len(x)):
        w,v=y[i,:]
        z[i,:] = torch.tensor([torch.sin(w),torch.sin(v)])+u[i]
    return z


'''
For learning 
'''

N = args.N  # sample size
D_in = 4  # input dimension
H1 = 4 * D_in  # hidden dimension
D_out = 2  # output dimension
torch.manual_seed(10)
Data = torch.Tensor(N,4).uniform_(-5,5)
# theta = 0.8
max_iters = 500


start = timeit.default_timer()
for k in range(0,19):
    theta = float(format(k*0.05+0.05,'.2f'))
    data = get_batch(Data)
    out_iters=0
    while out_iters < 1:
        # break
        model = ControlNet(D_in,H1,D_out)
        i = 0
        t = 0
        learning_rate = args.lr
        optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)

        while i < max_iters:
            s_u = model(data)
            f = f_(data)
            g = g_(data,s_u)
            x = data[:,0:2]
            # loss = (2-theta)*torch.diagonal(torch.mm(x, g.T))**2-torch.diagonal(torch.mm(x,x.T))*torch.diagonal(
            #     2*torch.mm(x,f.T)+torch.mm(g,g.T))
            loss = (2-theta)*((x*g)**2)-x**2*(2*x*f+g**2)
            AS_loss = (F.relu(-loss)).mean()
            print(k,i, "AS loss=", AS_loss.item())
            optimizer.zero_grad()
            AS_loss.backward()
            optimizer.step()
            if AS_loss < 1e-5:
                break
            i += 1
        # print('\n')
        # print("Total time: ", stop - start)
        # print("Verified time: ", t)

        out_iters += 1

    stop=timeit.default_timer()
    print('\n')
    print("Total time: ",stop-start)
    torch.save(model.state_dict(),'./data/S_{}.pkl'.format(theta))

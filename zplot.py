import numpy as np
from matplotlib import pyplot as plt
import matplotlib.tri as tri

def do():
    
      def f(x, z1, z2):
    
          alpha_np = alpha/8.686
          beta = 2*np.pi*80e6*np.sqrt(eps)/3e8
          #Zs = 50*np.tanh(alpha_np*x+beta*x)
          Zs = 50*np.tanh(alpha_np*x+1j*beta*x)
          Zl = z1+1j*z2
          Z_IN = Zs*Zl/(Zs+Zl)
          
          return np.abs((Z_IN-50)/(Z_IN+50))**2
    
      num_z1=num_z_re
      num_z2=num_z_im
      z1_0=z_re_0
      z2_0=z_im_0
      
      #x = np.linspace(0,1, num=num_x)*np.pi
      x = np.linspace(0, l_max, num=num_x)
      
      if z_re_log:
        z1 = z1_0+np.logspace(z_re_pow1, z_re_pow2, num=num_z1)
      else:
        z1 = np.linspace(z_re_min, z_re_max, num=num_z1)
      
      if z_im_log:
        z2 = z2_0+np.logspace(z_im_pow1, z_im_pow2, num=num_z2)
      else:
        z2 = np.linspace(z_im_min, z_im_max, num=num_z2)
      
      Z1, Z2, X = np.meshgrid(z1, z2, x, indexing='ij') 
      Y=f(X, Z1, Z2)
    
      z1_m_raw, z2_m_raw, x_m_raw = np.where(Y<=ymin)
      #print(x[x_m])
      z1_m_raw=z1[z1_m_raw]
      z2_m_raw=z2[z2_m_raw]
      x_raw = x[x_m_raw]
      k = z1_m_raw[0]
      m = z2_m_raw[0]
      c = 0
      x_tmp = [x_raw[0]]
      z1_m, z2_m, w_m, x_m = [k], [m], [], []
    
      for i in range(len(x_m_raw)):
          if z1_m_raw[i]==k and z2_m_raw[i]==m:
              x_tmp.append(x_raw[i])
              c+=1
          else:
              if len(x_tmp)==0:
                  print('in for')
              x_m.append(np.mean(x_tmp))
              x_tmp = [x_raw[i]]
              w_m.append(c)
              c=1
              z1_m.append(z1_m_raw[i])
              z2_m.append(z2_m_raw[i])
              k=z1_m[-1]
              m=z2_m[-1]
      if len(x_tmp)==0:
          print('after for')
      x_m.append(np.mean(x_tmp))
      w_m.append(c)
      z1_m=np.array(z1_m)
      z2_m=np.array(z2_m)
      '''
      from scipy import interpolate
      interp = interpolate.interp2d(z1_m, z2_m, w_m, bounds_error=False, 
                                    fill_value=0, kind='quintic')
      
      Z1, Z2 = np.meshgrid(z1, z2)
      w=np.empty_like(Z1)
      for i in range(Z1.shape[0]):
          for j in range(Z1.shape[1]):
              w[i, j]=interp(Z1[i,j], Z2[i,j])
      w[w<1]=0    
      w[w>np.max(w_m)] = np.max(w_m)
      #w*=(180/num_x)
      '''
    
      plt.figure(figsize=(10, 10))
      #plt.contourf(z1, z2, w)
      #return z1_m, z2_m, w_m, x_m, 
      # Create the Triangulation; no triangles so Delaunay triangulation created.
      triang = tri.Triangulation(z1_m, z2_m)
    
      # Mask off unwanted triangles.
      triang.set_mask(np.hypot(z1_m[triang.triangles].mean(axis=1)-15,
                               z2_m[triang.triangles].mean(axis=1))
                               < 15)
      plt.tricontourf(triang, x_m)
      plt.colorbar()
      plt.tricontour(z1_m, z2_m, w_m)
      if plot_points:
        plt.plot(z1_m, z2_m, '.', color='red')
      plt.xlabel("$Re(Z_L)$")
      plt.ylabel("$Im(Z_L)$")
      if z_re_log:
        plt.xscale('log')
      if z_im_log:
        plt.yscale('log')
      
      plt.savefig('zplot.png')
      plt.show()
      return z1_m, z2_m, w_m, x_m
      

'''
USER INPUT
'''
ymin=0.05         # ksqr<ymin
num_x=1000        # resolution of x (number of points from 0 to Pi) 
num_z_re=1000      # resolution of real part of z2
num_z_im=1000      # resolution of imaginary part of z2
z_re_min=0        # real part of z belong [z_re_min, z_re_max]
z_re_max=120      # real part of z belong [z_re_min, z_re_max]
z_im_min=-100     # image part of z belong [z_im_min, z_im_max]

z_im_max=100      # image part of z belong [z_im_min, z_im_max]
z_re_log=False    # logarifm scale of real axis. if True - real part of z2 belong to [z_re_0+10^z_re_pow1, z_re_0+10^z_re_pow2]
z_im_log=False    # logarifm scale of image axis. if True - image part of z2 belong to [z_im_0+10^z_im_pow1, z_im_0+10^z_im_pow2]
z_re_pow1=-5      # set if z_re_log=True, else will be ignored
z_re_pow2=3       # set if z_re_log=True, else will be ignored
z_im_pow1=0       # set if z_im_log=True, else will be ignored
z_im_pow2=1       # set if z_im_log=True, else will be ignored
z_re_0=0          # set if z_re_log=True, else will be ignored; real part of z2 belong to [z_re_0+10^z_re_pow1, z_re_0+10^z_re_pow2]
z_im_0=-15        # set if z_im_log=True, else will be ignored; image part of z2 belong to [z_im_0+10^z_im_pow1, z_im_0+10^z_im_pow2]

alpha = 0.3      # dB/m cable attenuation
eps = 2.5

l_max = 3e8/(80e6*np.sqrt(eps))/2

plot_points=False
###
z1_m, z2_m, w_m, x_m = do()
'''
    All functions in this file are copied from a MATLAB version
    provided by Dar et al. [https://arxiv.org/abs/1310.6137]
    and translated into Python.

    Please cite the above appropriately if used.
'''

import numpy as np
import claude.utils as cu

c = 299792458
h = 6.6261e-34

def defaultParameters(D=16.4640, Fc=1.9341e+14):
    # D = 16.4640 # makes beta2 = 21

    lambda_ = c/Fc
    beta2 = D*1e-6*lambda_**2/(2*np.pi*c)*1e27

    param = cu.AttrDict()
    param.lambda_ = lambda_ # Wavelength
    param.Fc = Fc           # Carrier frequncy
    param.PolMux = 1        # 0 when single polarization, 1 with polarization multiplexing
    param.gamma = 1.3       # Nonlinearity coefficient in [1/W/km]
    param.D     = D   
    param.beta2 = beta2     # Dispersion coefficient [ps^2/km]
    param.alpha = 0.2       # Fiber loss coefficient [dB/km]
    param.Nspan = 20        # Number of spans
    param.L = 100           # Span length [km]
    param.PD = 0            # Pre-dispersion [ps^2]
    param.PdBm = 2          # Average input power [dBm]
    param.BaudRate = 32     # Baud-rate [GHz]
    param.ChSpacing = 50    # Channel spacing [GHz]
    param.kur = 1.32        # Second order modulation factor <|a|^4>/<|a|^2>^2
    param.kur3 = 1.96       # Third order modulation factor <|a|^6>/<|a|^2>^3
    param.N_mc = int(1e6)   # Number of integration points in algorithm
    param.NF = 5            # EDFA Noise figure

    return param

def calcAseNoisePower(param):
    G = param.L*param.alpha
    AseNoiseDensity = param.Nspan*(param.PolMux+1)*h*c/param.lambda_*10**(param.NF/10)/2*(10**(G/10)-1) 
    AseNoisePower = param.BaudRate*1e9*AseNoiseDensity
    return AseNoisePower

def normalizeParameters(param):
    param.alphaNorm = param.alpha/10*np.log(10)
    param.T  = 1000/param.BaudRate
    param.P0 = cu.dB2lin( param.PdBm, 'dBm' )
    param.beta2Norm = param.beta2/param.T**2
    param.PDNorm = param.PD/param.T**2
    param.ChSpacingNorm = param.ChSpacing/param.BaudRate
    
    return param

def _calcIntra(param,argInB,R):
    
    gamma  = param.gamma
    beta2  = param.beta2Norm
    alpha  = param.alphaNorm
    Nspan  = param.Nspan
    L      = param.L
    PD     = param.PDNorm
    N      = param.N_mc
    
    ## calculate X1    
    arg1 = (R[1,:]-R[2,:])*(R[1,:]-R[0,:])
    argPD1 = arg1
    ss1 = np.exp(1j*argPD1*PD)*(np.exp(1j*beta2*arg1*L-alpha*L)-1)/(1j*beta2*arg1-alpha)
    s1 = np.abs(ss1*(1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L)))**2
    X1 = np.sum(s1*argInB)*(gamma**2)/N

    ## calculate X0
    s0 = ss1*(1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))
    X0 = np.abs(np.sum(s0*argInB)/N)**2*(gamma**2)

    ## calculate X2
    w1 = -R[1,:]+R[3,:]+R[2,:]
    arg2 = (R[1,:]-R[2,:])*(R[3,:]-R[0,:])
    argPD2 = arg2
    ss2 = np.exp(-1j*argPD2*PD)*(np.exp(-1j*beta2*arg2*L-alpha*L)-1)/(-1j*beta2*arg2-alpha)*(w1<np.pi)*(w1>-np.pi)
    s2 = (1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))*ss1*(1-np.exp(-1j*Nspan*arg2*beta2*L))/(1-np.exp(-1j*arg2*beta2*L))*ss2
    X2 = np.real(np.sum(s2*argInB))*(gamma**2)/N

    ## calculate X21
    w2 = R[3,:]-R[0,:]-R[2,:]
    arg2 = (R[1,:]-R[3,:])*(R[1,:]-w2)
    argPD2 = arg2
    ss2 = np.exp(-1j*argPD2*PD)*(np.exp(-1j*beta2*arg2*L-alpha*L)-1)/(-1j*beta2*arg2-alpha)*(w2<np.pi)*(w2>-np.pi)
    s21 = (1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))*ss1*(1-np.exp(-1j*Nspan*arg2*beta2*L))/(1-np.exp(-1j*arg2*beta2*L))*ss2
    X21 = np.real(np.sum(s21*argInB))*(gamma**2)/N

    ## calculate X3
    w3 = R[0,:]-R[1,:]+R[3,:]+R[2,:]-R[4,:]
    arg3 = (R[3,:]-R[4,:])*(R[3,:]-w3)
    argPD3 = arg3
    ss3 = np.exp(-1j*argPD3*PD)*(np.exp(-1j*beta2*arg3*L-alpha*L)-1)/(-1j*beta2*arg3-alpha)*(w3<np.pi)*(w3>-np.pi)
    s3 = (1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))*ss1*(1-np.exp(-1j*Nspan*arg3*beta2*L))/(1-np.exp(-1j*arg3*beta2*L))*ss3
    X3 = np.real(np.sum(s3*argInB))*(gamma**2)/N
    
    return np.hstack( (X0,X1,X2,X21,X3) )

def calcIntraConstants(param):
    param = normalizeParameters(param)

    N = param.N_mc

    R = 2*np.pi*(np.random.rand( 5, N )-0.5*np.ones( (5, N) ))
    w0 = R[0,:]-R[1,:]+R[2,:]
    argInB = (w0<np.pi)*(w0>-np.pi)
    return _calcIntra(param,argInB,R)

def calcIntraConstantsAddTerms(param):
    param = normalizeParameters(param)

    N = param.N_mc
    q = param.ChSpacingNorm

    R = 2*np.pi*(np.random.rand( 5, N )-0.5*np.ones( (5, N) ))
    w0 = R[0,:]-R[1,:]+R[2,:]
    argInB = (w0<np.pi+2*np.pi*q)*(w0>-np.pi+2*np.pi*q)
    return _calcIntra(param,argInB,R)

def calcInterConstants(param):
    param = normalizeParameters(param)
    
    gamma  = param.gamma
    beta2  = param.beta2Norm
    alpha  = param.alphaNorm
    Nspan  = param.Nspan
    L      = param.L
    PD     = param.PDNorm
    N      = param.N_mc
    q      = param.ChSpacingNorm
    
    R = 2*np.pi*(np.random.rand(4,N)-0.5*np.ones((4, N)))
    Volume = (2*np.pi)**4

    ## calculate chi1
    w0 = R[0,:]-R[1,:]+R[2,:]
    arg1 = (R[1,:]-R[2,:])*(R[1,:]+2*np.pi*q-R[0,:])
    argPD1 = arg1
    ss1 = np.exp(1j*argPD1*PD)*(np.exp(1j*beta2*arg1*L-alpha*L)-1)/(1j*beta2*arg1-alpha)*(w0<np.pi)*(w0>-np.pi)
    s1 = np.abs(ss1*(1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L)))**2/Volume
    avgF1 = np.sum(s1)/N
    chi1 = avgF1*Volume*(4*gamma**2)
    
    ## calculate chi2
    w3p = -R[1,:]+R[3,:]+R[2,:]+2*np.pi*q
    arg2 = (R[1,:]-R[2,:])*(R[3,:]-R[0,:]+2*np.pi*q)
    argPD2 = arg2
    ss2 = np.exp(-1j*argPD2*PD)*(np.exp(-1j*beta2*arg2*L-alpha*L)-1)/(-1j*beta2*arg2-alpha)*(w3p>-np.pi+2*np.pi*q)*(w3p<np.pi+2*np.pi*q)
    s2 = (1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))*ss1*(1-np.exp(-1j*Nspan*arg2*beta2*L))/(1-np.exp(-1j*arg2*beta2*L))*ss2/Volume
    avgF2 = np.real(sum(s2))/N
    chi2 = avgF2*Volume*(4*gamma**2)
    
    return np.array( [chi1,chi2] )

def calcInterConstantsAddTerms(param):
    param = normalizeParameters(param)

    gamma  = param.gamma
    beta2  = param.beta2Norm
    alpha  = param.alphaNorm
    Nspan  = param.Nspan
    L      = param.L
    PD     = param.PDNorm
    N      = param.N_mc
    q      = param.ChSpacingNorm

    R = 2*np.pi*(np.random.rand(4,N)-0.5*np.ones((4, N)))

    ## calculate X21
    w0 = R[0,:]-R[1,:]+R[2,:]+2*np.pi*q
    arg1 = (R[1,:]-R[2,:]-2*np.pi*q)*(R[1,:]-R[0,:])
    argPD1 = arg1
    ss1 = np.exp(1j*argPD1*PD)*(np.exp(1j*beta2*arg1*L-alpha*L)-1)/(1j*beta2*arg1-alpha)*(w0<np.pi)*(w0>-np.pi)
    s1 = np.abs(ss1*(1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L)))**2
    X21 = np.sum(s1)*gamma**2/N

    ## calculate X22
    w1 = R[0,:]-R[1,:]+R[3,:]
    arg2 = (w1-R[2,:]-2*np.pi*q)*(R[1,:]-R[0,:])
    argPD2 = arg2
    ss2 = np.exp(-1j*argPD2*PD)*(np.exp(-1j*beta2*arg2*L-alpha*L)-1)/(-1j*beta2*arg2-alpha)*(w1<np.pi)*(w1>-np.pi)
    s2 = (1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))*ss1*(1-np.exp(-1j*Nspan*arg2*beta2*L))/(1-np.exp(-1j*arg2*beta2*L))*ss2
    X22 = np.real(np.sum(s2))*gamma**2/N

    ## calculate X23
    w2 = R[0,:]+R[1,:]-R[2,:]-2*np.pi*q
    arg1 = (R[2,:]+2*np.pi*q-R[1,:])*(R[2,:]+2*np.pi*q-R[0,:])
    argPD1 = arg1
    ss3 = np.exp(1j*argPD1*PD)*(np.exp(1j*beta2*arg1*L-alpha*L)-1)/(1j*beta2*arg1-alpha)*(w2<np.pi)*(w2>-np.pi)
    s3 = np.abs(ss3*(1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L)))**2
    X23 = np.sum(s3)*gamma**2/N

    ## calculate X24
    w3 = R[0,:]-R[3,:]+R[1,:]
    arg2 = (R[2,:]+2*np.pi*q-R[3,:])*(R[2,:]+2*np.pi*q-w3)
    argPD2 = arg2
    ss4 = np.exp(-1j*argPD2*PD)*(np.exp(-1j*beta2*arg2*L-alpha*L)-1)/(-1j*beta2*arg2-alpha)*(w3<np.pi)*(w3>-np.pi)
    s4 = (1-np.exp(1j*Nspan*arg1*beta2*L))/(1-np.exp(1j*arg1*beta2*L))*ss3*(1-np.exp(-1j*Nspan*arg2*beta2*L))/(1-np.exp(-1j*arg2*beta2*L))*ss4
    X24 = np.real(np.sum(s4))*gamma**2/N

    return np.hstack( (X21,X22,X23,X24) )

def calcInterChannelNLIN(chi,param):
    param = normalizeParameters(param)

    if chi.ndim==1:
        chi = np.expand_dims(chi,1)

    NLIN_inter = chi[0,:]+(param.kur-2)*chi[1,:]
    if param.PolMux == 1:
        NLIN_inter = 16/81*(NLIN_inter+2*chi[0,:]/4+(param.kur-2)*chi[1,:]/4)
    NLIN_inter = param.P0**3*NLIN_inter

    return NLIN_inter

def calcInterChannelNLINAddTerms(X,param):
    param = normalizeParameters(param)

    if X.ndim==1:
        X = np.expand_dims(X,1)

    NLIN_inter_addTerms = 4*X[0,:]+4*(param.kur-2)*X[1,:]+2*X[2,:]+(param.kur-2)*X[3,:]
    if param.PolMux == 1:
        NLIN_inter_addTerms = 16/81*(NLIN_inter_addTerms+2*X[0,:]+(param.kur-2)*X[1,:]+X[2,:]+0*(param.kur-2)*X[3,:])
    NLIN_inter_addTerms = param.P0**3*NLIN_inter_addTerms
    return NLIN_inter_addTerms

def calcIntraChannelNLIN(X,param):
    param = normalizeParameters(param)

    if X.ndim==1:
        X = np.expand_dims(X,1)

    NLIN_intra = 2*X[1,:]+(param.kur-2)*(4*X[2,:]+X[3,:])+(param.kur3-9*param.kur+12)*X[4,:]-(param.kur-2)**2*X[0,:]
    if param.PolMux == 1:
        NLIN_intra = 16/81*(NLIN_intra+X[1,:]+(param.kur-2)*X[2,:])
    NLIN_intra = param.P0**3*NLIN_intra
    return NLIN_intra

def calcInterChannelGN(chi,param):
    param = normalizeParameters(param)

    if chi.ndim==1:
        chi = np.expand_dims(chi,1)

    NLIN_inter = chi[0,:]
    if param.PolMux == 1:
        NLIN_inter = 16/81*(NLIN_inter+2*chi[0,:]/4)
    NLIN_inter = param.P0**3*NLIN_inter
    return NLIN_inter

def calcIntraChannelGN(X,param):
    param = normalizeParameters(param)

    if X.ndim==1:
        X = np.expand_dims(X,1)

    NLIN_intra = 2*X[1,:]
    if param.PolMux == 1:
        NLIN_intra = 16/81*(NLIN_intra+X[1,:])
    NLIN_intra = param.P0**3*NLIN_intra
    return NLIN_intra
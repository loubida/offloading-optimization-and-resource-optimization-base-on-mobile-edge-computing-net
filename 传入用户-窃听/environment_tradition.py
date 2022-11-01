import numpy as np
import pandas as pd
import copy
import math

# S=[任务量✖️卸载率，总算力，总功率]
# A=[卸载率1增，卸载率1减，卸载率2增，卸载率2减，。。。]


class environment1(object):  # 奖励r由tc与tc-1比较大小得出。Hn：0.992912817258564,	0.992299817945962
    def __init__(self, user_num, cap_num, W, f_local, omega, F_cap, p_local, p_tran, lamuda, noise, Hn_0,Hn_1,Hn_e,user_l, suspend):
        # user_num:用户总数, cap_num:cap总数,W:单个CAP的总带宽,f_local为本地用户计算能力,omega:计算时间T的w
        # C为计算时间的传输速率,F_cap:分配给user的计算能力,p_local:本地计算功率,p_tran：传输功率;lamuda:时间与能耗之间的比例系数
        # noise:噪音的方差，用于计算香农公式的C;Hn:香农公式的hnm，用于计算C。suspend:用于判断执行多少次动作后停止
        self.user_num = user_num
        self.cap_num = cap_num

        self.f = f_local
        self.omega = omega

        #W为总带宽，[capA,capB]，需要取出来
        self.W0 = W
        self.W1 = W

        # F_cap为算力（优化对象），[CAPA,CAPB]，需分别均分给n个设备

        self.F_cap=F_cap
        self.F_0 = F_cap[0][0] / self.user_num#均分算力
        self.F_1 = F_cap[0][1] / self.user_num#均分算力



        self.F_capA = np.full(shape=(1,self.user_num),fill_value=self.F_0)#capA均分给每一个user的算力
        self.F_capB = np.full(shape=(1, self.user_num), fill_value=self.F_1)  #capB均分给每一个user的算力

        #传输带宽（优化对象）,p_tran总传输功率[user1,user2]
        self.p_tran = p_tran
        p_tran_0 = self.p_tran[0][0] / self.cap_num
        p_tran_1 = self.p_tran[0][1] / self.cap_num

        self.p_tran_user1 = np.full(shape=(1, self.cap_num), fill_value=p_tran_0)  # 第一个user分给不同信道的传输功率
        self.p_tran_user2 = np.full(shape=(1, self.cap_num), fill_value=p_tran_1)  # 第二个user分给不同信道的传输功率

        self.p_tran_capA = np.array([[self.p_tran_user1[0][0], self.p_tran_user2[0][0]]])  # 第一个cap对应每一个user的传输功率
        self.p_tran_capB = np.array([[self.p_tran_user1[0][1], self.p_tran_user2[0][1]]])  # 第二个cap对应每一个user的传输功率
        

        #信道，Hn为总信道[CAP]
        self.Hn_0=Hn_0.reshape(1,2)
        self.Hn_1=Hn_1.reshape(1,2)

        self.suspend = suspend

        #分配任务量
        self.user_l = user_l#用户最少2个

        #窃听者
        self.Hn_e=Hn_e.reshape(1,2)

        #卸载率初始化：

        self.user_offrate = np.zeros(shape=(1,(cap_num + 1)*user_num))#user_offrate的shape[1,(cap_num + 1)*user_num]
        for i in range((cap_num + 1)*user_num):
            if i % (cap_num + 1)==0:
                self.user_offrate[0][i] = 1.0
        self.judge=self.user_offrate
        # print("初始化时的卸载率为：", self.user_offrate)

        # self.user_offrate_ABC=copy.deepcopy(self.user_offrate)

        self.lamuda = lamuda
        self.noise = noise
        self.i = 0
        self.cost_list = []  # 记录成本
        self.epoch_list = []
        self.quancost_list = []
        self.wucost_list = []

        self.task_action = 1  # 任务每次变化率（任务卸载率）
        self.Mb_to_bit = 2 ** 20  # Mb to bit 1MB = 1024KB = 1024*1024B = 1024 * 1024 *8 bit =2^23
        # self.Mb_to_bit = 1  # Mb to bit 1MB = 1024KB = 1024*1024B = 1024 * 1024 *8 bit =2^23
        self.p_local = p_local

        #--------------------------
        #窃听者


        #-------------------------






        # self.l1=np.full(shape=(1, self.cap_num + 1), fill_value=self.user_l[0][0])
        # self.l2 = np.full(shape=(1, self.cap_num + 1), fill_value=self.user_l[0][1])
        self.l=np.append(np.full(shape=(1, self.cap_num + 1), fill_value=self.user_l[0][0]),np.full(shape=(1, self.cap_num + 1), fill_value=self.user_l[0][1]),axis=1)
        self.A = 1.0
        self.B = 0.0
        self.C = 0.0
        self.D = 1.0
        self.E = 0.0
        self.F = 0.0

        self.temp_tc1 = self.total_cost(self.user_offrate)
        self.tc_wald = self.total_cost(self.user_offrate)
        # print("本地的cost为：", self.temp_tc1)








    def reset(self):  # 重开，返回初始化s

        #卸载率✖️任务量
        self.user_S = self.l * self.user_offrate  #任务量，1x6
        #总功率和总算力：p_tran[0],p_tran[1]，F_cap[0]，F_cap[1]
        self.P_F=np.append(self.p_tran,self.F_cap,axis=1)
        #信道差
        self.Hn0_diff=self.Hn_0-self.Hn_e
        self.Hn1_diff=self.Hn_1-self.Hn_e
        self.Hn_diff=np.append(self.Hn0_diff,self.Hn1_diff,axis=1)

        S_=np.append(self.user_S,self.P_F,axis=1)

        S_=np.append(S_,self.Hn_diff,axis=1)
        return S_

    def step(self, action):
        # 输入动作，输出下一步状态s_，奖励r,是否结束done。得根据给的动作，得出下一步s_，还有r，并且r需要求出当前状态下的成本


        self.i = self.i + 1

        # 判断action执行什么动作,action为一个值

        # self.actions=int(action/2)#对应到卸载率的下标

        # if action%2==0:#增加
        #     self.offrate_normalization(self.actions,1)
        # else:#减少
        #     self.offrate_normalization(self.actions,0)

        if action == 0:  # user1本地增加
            self.offrate_normalization(0, 1)
        elif action == 1:
            self.offrate_normalization(1, 1)
        elif action == 2:  # user1-capB增加
            self.offrate_normalization(2, 1)
        elif action == 3:
            self.offrate_normalization(3, 1)
        elif action == 4:  # user2-capA增加
            self.offrate_normalization(4, 1)
        else:
            self.offrate_normalization(5, 1)


        s_ = self.l * self.user_offrate
        self.P_F = np.append(self.p_tran, self.F_cap, axis=1)
        s_ = np.append(s_, self.P_F, axis=1)
        s_=np.append(s_,self.Hn_diff,axis=1)
        tc = self.total_cost(self.user_offrate)  # 更新后的卸载率的成本

        if tc > self.tc_wald:  # tc为更新后的成本，tc_wald为更新前的成本
            r = -100
        elif tc < self.tc_wald:
            r = 100
        else:
            r = -100
        self.user_S = s_  # 更新状态
        # if self.i % 500==0:
        #     print("----------------------------------")
        #     print("执行了第", self.i, "次动作")
        #     print("此轮更新卸载率后的成本为:", tc)
        #     print("此时卸载率为：", self.user_offrate)


        self.tc_wald = tc

        done = 0  # 不知道什么情况 done输出Ture，代码也没写
        if self.i == self.suspend:
            done = self.tc_wald
            self.i = 0



        return s_, r, done, self.tc_wald,self.temp_tc1

    #根据动作，改变对应的卸载率
    def offrate_normalization(self,number,add_subtraction):#如增加，add_subtraction=1
        if add_subtraction:
            if number==0:
                self.A+=1.0
            elif number==1:
                self.B+=1.0
            elif number==2:
                self.C+=1.0
            elif number==3:
                self.D+=1.0
            elif number==4:
                self.E+=1.0
            else:
                self.F+=1.0
        else:
            if number==0:
                if self.A>1:
                    self.A-=1.0
            elif number==1:
                if self.B>1:
                    self.B-=1.0
            elif number==2:
                if self.C>1:
                    self.C-=1.0
            elif number==3:
                if self.D>1:
                    self.D-=1.0
            elif number==4:
                if self.E>1:
                    self.E-=1.0
            else:
                if self.F>1:
                    self.F-=1.0
        self.user_offrate[0][0] = self.A/  (self.A+self.B+self.C)
        self.user_offrate[0][1] = self.B / (self.A + self.B + self.C)
        self.user_offrate[0][2] = self.C / (self.A + self.B + self.C)
        self.user_offrate[0][3] = self.D / (self.D + self.E + self.F)
        self.user_offrate[0][4] = self.E / (self.D + self.E + self.F)
        self.user_offrate[0][5] = self.F / (self.D + self.E + self.F)



    def action_state_num(self):  # 返回动作与环境个数
        action_n = self.user_num * (self.cap_num+1)#dqn

        Hn_num = self.cap_num * self.user_num
        state_num = self.user_num * (self.cap_num + 1) + self.cap_num * 2 + Hn_num
        return action_n, state_num

    def Time(self, user_offrate):
        # 计算香农公式Wn

        # # #-----优化带宽-------------
        # if self.user_offrate.all()!=0:
        #     W_user=np.sqrt((self.user_l*self.user_offrate*self.p_tran)/np.log2(1+(self.p_tran*np.square(self.Hn))/pow(self.noise, 2)))*self.W/np.sum(np.sqrt((self.user_l*self.user_offrate*self.p_tran)/np.log2(1+(self.p_tran*np.square(self.Hn))/pow(self.noise, 2))))
        # else:
        #     w_ = self.W / self.user_num
        #     W_user = np.full(shape=(1,self.user_num),fill_value=w_)
        # #-------------------

        #--------均分带宽--------------
        # w_0 = self.W0 / self.user_num#shape[1,2]
        # w_1 = self.W1 / self.user_num#shape[1,2]
        W_A_user = np.full(shape=(1, self.user_num), fill_value=self.W0)
        W_B_user = np.full(shape=(1, self.user_num), fill_value=self.W1)
        #-----------------------------

        C_A1=W_A_user*np.log2(1 + self.p_tran_capA * self.Hn_0 / pow(self.noise, 2))#[cap_A_user1,cap_A_user2]
        C_B1=W_B_user*np.log2(1 + self.p_tran_capB * self.Hn_1 / pow(self.noise, 2))

        #窃听者
        C_A_E=W_A_user*np.log2(1+self.p_tran_capA*self.Hn_e / pow(self.noise, 2))
        C_B_E = W_B_user * np.log2(1 + self.p_tran_capB * self.Hn_e / pow(self.noise, 2))

        #更新速率
        C_A=C_A1 - C_A_E
        C_B=C_B1 - C_B_E

        self.offrate_A = np.array([[user_offrate[0][1], user_offrate[0][4]]])  # shape:[用户1到capA的卸载率，用户2到capA的卸载率]
        self.offrate_B = np.array([[user_offrate[0][2], user_offrate[0][5]]])  # shape:[用户1到capA的卸载率，用户2到capA的卸载率]

        #本地
        self.offrate_local=np.array([[user_offrate[0][0],user_offrate[0][3]]])#shape:[本地用户1的卸载率，本地用户2的卸载率]
        self.T_local=self.user_l*self.offrate_local * self.omega * self.Mb_to_bit  / self.f#shape[1,2]

        # ----------CAPA--------------
        #传输

        self.T_tran_A=self.user_l * self.offrate_A  / C_A#shape[1,2]
        #CAP端
        self.T_cap_A=self.user_l * self.offrate_A * self.omega * self.Mb_to_bit / self.F_capA#shape[1,2]
        #----------CAPB--------------
        #传输

        self.T_tran_B=self.user_l * self.offrate_B / C_B#shape[1,2]
        #CAP端
        self.T_cap_B=self.user_l * self.offrate_B * self.omega * self.Mb_to_bit / self.F_capB#shape[1,2]
        # -----------------------------

        #求T
        T=np.sum(self.T_local)+np.sum(self.T_tran_A)+np.sum(self.T_cap_A)+np.sum(self.T_tran_B)+np.sum(self.T_cap_B)

        T_off_A=self.T_tran_A+self.T_cap_A

        # C = W_user * np.log2(1 + self.p_tran * self.Hn / pow(self.noise, 2))
        # temp = 1 - user_offrate
        # self.T_local = self.user_l * temp * self.omega * self.Mb_to_bit / self.f  # shape(1,num)
        # self.T_tran = self.user_l * user_offrate * self.omega * self.Mb_to_bit / C  # shape(1,num)
        # self.T_cap = self.user_l * user_offrate * self.omega * self.Mb_to_bit / self.F  # shape(1,num)
        # T_temp = self.T_tran + self.T_cap
        #
        # T_max = np.max(T_temp)
        # T_max1 = np.max(self.T_local)
        # T = max(T_max, T_max1)

        return T

    def Energy(self, ):
        self.E_local=self.T_local * self.p_local
        self.E_tran_A=self.T_tran_A * self.p_tran_capA
        self.E_tran_B=self.T_tran_B * self.p_tran_capB
        E=np.sum(self.E_local)+np.sum(self.E_tran_A)+np.sum(self.E_tran_B)

        # self.E_local = self.T_local * self.p_local
        # self.E_tran = self.T_tran * self.p_tran
        # self.E_total = self.E_tran + self.E_local
        # E = np.sum(self.E_total)
        return E

    def total_cost(self, user_offrate):  # total_cost 由T与E决定,返回当前时刻的成本
        T = self.Time(user_offrate)
        E = self.Energy()
        total_cost = self.lamuda * T
        return total_cost

    def cost_print(self):
        self.cost_list1 = self.cost_list  # 记录成本
        self.epoch_list1 = self.epoch_list
        self.quancost_list1 = self.quancost_list
        self.wucost_list1 = self.wucost_list
        self.cost_list = []  # 记录成本
        self.epoch_list = []
        self.quancost_list = []
        self.wucost_list = []
        return self.cost_list1, self.epoch_list1, self.quancost_list1, self.wucost_list1

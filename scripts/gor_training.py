#!/anaconda3/bin/python
import sys
import os
import glob
import pandas as pd
# To ensure that non of the outputs are truncated with '...'
pd.set_option('display.max_rows', None)
pd.set_option('display.max_columns', None)
pd.set_option('display.width', None)
pd.set_option('display.max_colwidth', None)
import numpy as np
# Rendering nicer tables
from IPython.display import display
import argparse 
import time

start_time = time.time()

def make_zero_array(window_size):
    '''
    Takes window size as arguments.
    Makes an array that has as many lines as the win_size and 
    the number of columns is defined by the number of naturally 
    occurring aa in eukaryotes. Returns the array.
    '''
    array = np.zeros((window_size,20)) #, dtype= 'float64' is allready default - not necessary to specify!!!
    return array


def make_frequency_df(zeroarray):
    '''
    Makes dataframe from zero array to better vizualize whats going on.
    Enables us to index columns by residue name.
    '''
    header_col = ['A', 'R', 'N', 'D', 'C', 'Q', 'E', 'G', 'H', 'I', 'L', 'K', 'M', 'F', 'P', 'S', 'T', 'W', 'Y', 'V']
    # row_names = ['R_0'] #['#R,H', '#R,E', '#R,C', '#R'] # want to implement using -1 0 1 according to window....
    #     freq_array = make_zero_array(win_size)
    freq_df = pd.DataFrame(data = zeroarray,  columns=header_col) # index=row_names
    return freq_df

def read_clean_all(infile1):
    ''' Reads ALL lines from a file. Returns string of second line. The '\n' is stripped.'''
    with open(infile1, 'r') as rfile:
        newline_list = rfile.readlines()
        clean =[]
        for l in newline_list:
            clean.append(l.rstrip())
        return clean

def read_clean_lines(infile1):
    ''' Reads ONLY second line from a file. Returns string of second line. The '\n' is stripped.'''
    with open(infile1, 'r') as rfile:
        newline_list = rfile.readlines()
        cleanstring = newline_list[1].rstrip()
        return cleanstring


def train_gor(profile_infile, ssfile, RH, RE, RC, total_R, total_SS, win_size):
    '''
    Takes as input: (1) seq profile file (2) fasta like dssp file (3) arrays comprising the gor model 
    -> RH, RE, RC, total_R (all 4 np.arr) and total_SS which is a pd.df . The seq profile file (1) is 
    read into np.array. The ss string is extracted from fasta like dssp file (2). The corresponding 
    positions are incremented according to R in given conformation in each field. Returns the trained GOR model.
    RH, RE, RC, total_SS as np.arr and total_SS as pd.df.
    '''
    # Loading profile_infile into np.array, need to indicate range 20 to get rid of last col containing 'nan'
    profile_arr = np.loadtxt(profile_infile, usecols=range(0,20), dtype=np.float64) 

    # Creating overhang before and after profile__array accouning for window size!
    overhang = win_size//2
    overhang_arr = np.zeros((overhang, 20)) 
    overhang_profile_arr = np.concatenate((overhang_arr, profile_arr, overhang_arr), axis=0)
    # print(overhang_profile_arr) 

    ss_string = read_clean_lines(ssfile) # Reads ss string from fastalike file (2)
    # print(ss_string)                                        
    
    rows = profile_arr.shape[0]                  #  tuple --> using var rows only = index 0

    if len(ss_string) != rows:                      # len(ss_string) must be == number of rows in profile_arr
        print('Error: length not the same as in profile! ', ssfile)
        print('Error: length not the same as in ss file! ', profile_infile)
        return RH, RE, RC, total_R, total_SS

    for i in range(rows):
        # Iterates over the overhang_profile generating new window each time
        # The window is a slice from index i up to i+window_size 
        curr_window_arr = overhang_profile_arr[i:(i+win_size)]          # Window arr at index i

        ss = ss_string[i]                   # Holds type of secondary structure at index i

        total_SS['tot'] += 1                # Incrementing cell holding the total number of residues used

        total_R += curr_window_arr          # Incrementing each df by adding the entire window of the profile
        
        if ss == 'H':
            RH += curr_window_arr
            total_SS[ss] += 1

        elif ss == 'E':
            RE += curr_window_arr
            total_SS[ss] += 1

        else:                               
            RC += curr_window_arr
            total_SS['C'] += 1                # If not H or E --> e.g. '-' its assigned to 'C' compatible with both training and blind files
        
    return RH, RE, RC, total_R, total_SS

def listdir_nohidden(path):
    '''
    To ignore hidden files from os.listdir.
    Returns only 'nonhidden files' from directory
    --> the glob pattern * matches all files that are NOT hidden
    '''
    return glob.glob(os.path.join(path, '*'))

parser = argparse.ArgumentParser(description='Train GOR model')
parser.add_argument('-p', '--profile', type=str, metavar='', required=True, help='Path to directory containing all profile files needed for training.')
parser.add_argument('-s', '--secondarystructure', metavar='', type=str, required=True, help='Path to directory containing all secondary structures in fasta-like format needed for training.')
parser.add_argument('-i', '--ids', type=str, metavar='', required=False, help='Path to file containing IDs of current training set.')
parser.add_argument('-w', '--winsize', type=int,  metavar='', default=17, nargs='?', const=17, help='Window size of the sliding window for training the gor model. Default value = 17. Must be **ODD** numbered integer!') 
parser.add_argument('-o', '--output', type=str, metavar='', required=True, help='Path to training output directory.')
args = parser.parse_args()

if __name__ == '__main__':
    
    # 3 lists --> to loop on. 1: Training splits 2. profile files and 3. ss list.
    trainsplits = listdir_nohidden(args.ids).sort()   # Creating list of all cross validation lists 0..4
    pro_path = args.profile                # Creating list of all fasta files in folder
    ss_path = args.secondarystructure      # Creating list of all ss structure files
    win_size = args.winsize
    out_path = args.output                                    # To be added to outfile
    if win_size%2 == 0:                                       # Break it if entered number not odd
        sys.exit("Error: Window size must be an odd number!!!")
   
    id_l = read_clean_all(args.ids)
    # listdir: returns arbitrary order --> need to sort lists before continuing --> MUST .sort()
    # pro_files.sort()
    # ss_files.sort()
    # print(pro_files)
    # print('\n')
    # print(ss_files)
    # print(type(args.fasta))
    # print(args.secondarystructure)
    
    #############################################################################   
    # Generating arrays holding the counts of residue in conformation X --> R_X #
    #############################################################################   
    R_H = make_zero_array(win_size)           
    R_E = make_zero_array(win_size)
    R_C = make_zero_array(win_size)
    R_count = make_zero_array(win_size)       # generating array holding the total residue count
    # Generating smaller array holding the total secondary structure count
    ss_array = np.zeros((1,4)) # array holds total n of R in H, E or C and one cell for the total amount as checksum

    ################################################################################################
    # Converting ONLY ss_array to dataframe holding the total counts of SS in conformations H,E,C  #
    ################################################################################################
    # generating smaller dataframe holding the total counts conformations
    df_all_SS = pd.DataFrame(data=ss_array, columns=['H', 'E', 'C', 'tot'], index= ['#S'])
    # print("HEC df")
    # print(df_all_SS)
    
    # print("********"+'\n', pro_files)
    # print(id_l)
    for i in range(len(id_l)):
        # print("id: ", id_l[i])
        curr_profile = os.path.join(pro_path, id_l[i])+'.profile'
        curr_ss = os.path.join(ss_path, id_l[i])+'.dssp'
        # print('curr_profile', curr_profile)
        # print('curr_ss', curr_ss)
        train_gor(curr_profile, curr_ss, R_H, R_E, R_C, R_count, df_all_SS, win_size)
    
    # --------------------------------------------------------------------------------------------------------
    # Generating probablilities by dividing each row R_SS_d by the sum of the corresponding row d in R_count.
    # (d goes from 0 - 16). Returns probablilites of RH, RE, RC. All arrays H, E, C and R need to be divided by 
    # the sum of each row in R!
    # --------------------------------------------------------------------------------------------------------
    sum_R = R_count.sum(axis=1).reshape(win_size, 1) # Computing sum of each row --> series
    probabilities_H = np.divide(R_H, sum_R)
    probabilities_E = np.divide(R_E, sum_R)
    probabilities_C = np.divide(R_C, sum_R)
    marginal_prob_R = np.divide(R_count, sum_R)
    # probabilities_H = df_R_H/float(df_all_SS['tot'])
    # probabilities_E = df_R_E/float(df_all_SS['tot'])
    # probabilities_C = df_R_C/float(df_all_SS['tot'])
    #marginal_prob_R = df_R_count/float(df_all_SS['tot'])
    marginal_prob_ss = df_all_SS/float(df_all_SS['tot'])
    
    # print("--- %s seconds ---" % (time.time() - start_time))
    elapsed_seconds = float(time.time() - start_time)
    if elapsed_seconds > 60:
        minutes = elapsed_seconds/60
        print("--- %s minutes ---" % minutes)
    else:
        print("--- %s seconds ---" % (time.time() - start_time))

    # Saving arrays holding probabilities of R in S and #R to csv
    np.savetxt(os.path.join(out_path,'gor_training_out_H'), probabilities_H) # saving to txt(out_path+'gor_training_out_H.csv')
    np.savetxt(os.path.join(out_path,'gor_training_out_E'), probabilities_E)
    np.savetxt(os.path.join(out_path,'gor_training_out_C'), probabilities_C)
    np.savetxt(os.path.join(out_path,'gor_training_out_marg_prob_R'), marginal_prob_R)

    # Data Frame (!) holding total frequecies of SS has a different format --> saing it to sepparate df
    marginal_prob_ss.to_csv(os.path.join(out_path,'gor_training_output_SS.csv'))

    # win_size to be passed to prediction.py
    win_size_array = np.array([win_size])
    np.savetxt(os.path.join(out_path, 'win_size'), win_size_array)


import os
import AM4py
import subprocess
import shutil
import sys
import datetime as dtm
#
'''
A script/class to set up and batch-run AM4 scenarios. Note that the Python part should be platform independent (and so
maybe should move to AM4py.py ??); the example executions will use environment variables that are clearly system dependent.
'''
#
# TODO:
#  1) move action to a "do it" function
#  2) handle parameters.
class Setup_and_run(object):
    def __init__(self, input_data_path=None, work_dir=None, pth_restart=None, pth_input=None, batch_job_name=None, nml_template='nml_input_template.nml',
        job_name='AM4_dev', input_nml='input.nml', n_cpu_atmos=96, copy_timeout=6000, modules=None,
        n_days_total=60, runtime_days=1, runtime_months=0, npx=97, npy=97, npz=33,
        is_restart=False, verbose=True, do_batch=True, slurm_directives={}, **kwargs):
        '''
        # process input parameters; setup and run. Maybe separate the setup, stage, run phases?
        '''
        print('** DEBUG locals(): {}'.format(locals()))
        #
        # default variable values; we'll reset any variables passed via **kwargs after
        #  default values are set:
        if input_data_path is None: input_data_path = os.path.join(os.environ['SCRATCH'], 'AM4', 'AM4_data3', 'AM4_run')
        if work_dir is None: work_dir = os.path.join(os.environ['SCRATCH'], 'AM4', 'workdir')
        if pth_restart is None: pth_restart = os.path.join(work_dir, 'RESTART')
        if pth_input is None: pth_input   = os.path.join(work_dir, 'INPUT')
        #
        if batch_job_name is None: batch_job_name = os.path.join(work_dir, 'AM4_batch_example.bs')
        #
        # add slurm kwds:
        #for ky,vl in kwargs.items():
        #    if ky.startswith('slurm_'):
        #        slurm_directives[ky[6:]]=vl

        #
        #is_restart = False
        #verbose = True
        #job_name = 'AM4_dev'
        #slurm_partition='cees'
        #input_nml = 'input.nml'
        #
        n_cpu_atmos = int(n_cpu_atmos)
        copy_timeout = int(copy_timeout)
        #nml_template='input_yoder_v101.nml'
        ##restart_date_dtm = dtm.datetime(1979,1,1,0,0,0)
        #
        # TODO: How do we count days? We might need to specify the start and end dates, or start date and a total
        #  duration.. but we probably need to specify the start and end somehow.
        n_days_total   = int(n_days_total)
        runtime_days   = int(runtime_days)
        runtime_months = int(runtime_months)
        #
        npx = int(npx)
        npy = int(npy)
        npz = int(npz)
        #
        do_batch = AM4py.is_true(do_batch)
        
        #
        print('** ** ** ** DEBUG do_batch:: {}'.format(do_batch))
        verbose=int(verbose)
        #
        # This is nominally a fast, slick way to update default variables, but:
        # 1) it is unorgiving and generally harder to use (ie, a typ-o in a var name won't throw an error)
        # 2) We have to go through the variables to handle type, and other things too, anyway, so we don't really save much.
        #
        # update with anything passed in kwargs
        #self.__dict__.update(kwargs)
        #
        #####
    #    output_log = os.path.join(work_dir, 'AM4py_job_{}.log'.format(job_name))
    #    if not os.path.isfile(output_log):
    #        with open(output_log, 'w') as fout:
    #            fout.write('# AM4py script log\n#!job_name={}\n'.format(job_name))
            #
        #
        # TODO: evaluate status of macro-job:
        #  how many days have we run? is it >= n_days_total? Evaluate current_date and/or elapsed time in
        #print('*** input_data_path: ', input_data_path). current date is easy; total elapsed time is harder, except to convert
        #  date strings to date and subtract. alternatively, there are time-steps in the working data files, ie
        #  {work_dir}/19790101.atmos_4xdaily.tile1.nc.0000, but I think the files in RESTART, ie RESTART/atmos_coupled.res.nc only shows
        #  the elapsed time (in fractional days) for that sub-run.
        #
        ABS = AM4py.AM4_batch_scripter(input_data_path=input_data_path, work_dir=work_dir, npes_atmos=n_cpu_atmos,
                                   job_name=job_name, batch_out=batch_job_name, modules=modules,
                                   slurm_directives=slurm_directives,
                                    verbose=verbose, **kwargs )
        #
        restart_date = ABS.get_restart_current_date()
        #restart_date_dtm = dtm.datetime(*(','.join(restart_date)) )
        if verbose:
            print('*** ABS_current_date: {}'.format(restart_date))
            print('*** ABS variables:')
            #
            for key,val in ABS.__dict__.items():
                print('{}: {}'.format(key,val))
        #
        zz = ABS.get_input_data(verbose=True)
        #
        # manage RESTART:
        # 1) fetch current_date from coupler_nml (see my_configs below)
        # 2) move contents of RESTART into INPUT. RESTART should be empty.
        #   TODO: move this functionality to the ABS object. maybe .queue_for_restart(), which will do this move and anything else we determine
        #    to be necessary later. At very least, it will be nice instructions in code.
        # 3) Do we need to manually append the timeseries data?
        #
        # TODO: Do we need to crack open a .res (coupler.res maybe?) file to read the current date? How do restarts work?
        #
        my_configs = {'coupler_nml':{'days':runtime_days, 'months':runtime_months, 'current_date':ABS.get_restart_current_date()}, 'fv_core_nml':{'npx':npx, 'npy':npy, 'npz':npz}}
        if is_restart:
            my_configs['fv_core_nml']['adjust_dry_mass'] = '.false.'
        #
        print('*** NML configs: {}'.format(my_configs))
        nml_out=os.path.join(ABS.work_dir, input_nml)
        my_nml = ABS.make_NML(nml_template=nml_template, nml_configs=[my_configs],
                          nml_out=nml_out )
        #
        #print('*** DEBUG: {}'.format(my_nml))
        print('*** DEBUG: nml created: {}'.format(nml_out))
        #
        # just in case... there area  number of places where we can accidentally remove this path, which the Sim apparently cannot
        #  create.
        if not os.path.isdir(pth_restart ):
            os.makedirs(pth_restart)
        #
        # queue restart:
        # TODO: Should not actually need the len() evaluation, but os.path calls are being sensitive and twitchy...
        if len(os.listdir(pth_restart)) > 0:
            #for filename in os.listdir(pth_restart):
            #    # TODO: thread this?
            #    # NOTE: since this is a mv operation, it should be automagically recursive on all elements:
            #    # this appears to throw an error if the file already exists. we can handle that, or just use a subprocess...
            #    shutil.move(os.path.join(pth_restart, filename), pth_input )
            sp_out = subprocess.run('mv -f {}/* {}/'.format(pth_restart, pth_input), shell=True, check=True,capture_output=True, timeout=copy_timeout)
        #
        #my_nml = NML_from_nml('input_yoder_v101.nml')
        if verbose:
            print('** my_nml[fv_core_nml]:' )
            print('** ', my_nml['fv_core_nml'])
            #print(my_nml.keys())
            #
            print('** batch_out: ', ABS.batch_out)
        #
        ABS.write_batch_script()
        #
        if do_batch:
            if verbose:
                print('** ** submitting batch job: {}'.format(ABS.batch_out))
            sbatch_output = subprocess.run('sbatch {}'.format(ABS.batch_out), shell=True, check=True, capture_output=True )

if __name__ == '__main__':
    #
    # am4_container_pathname=None, am4_exe='am4.x'
    # example (Sherlock, gfdl container):
    # NOTE: modules and hpc_config here are redundant.
    # srun --partition=serc --constraint=CLASS:SH3_CBASE python am4_runner.py input_data_path=`cd ..;pwd`/AM4_run work_dir=`cd ..;pwd`/workdir nml_template=input_xanadu_2021.01.nml n_cpu_atmos=24 modules=am4/singularity_gfdl/2021.1.0 hpc_config=sherlock3_base_singularity mpi_exec='srun' am4_container_pathname=${AM4_CONTAINER_PATHNAME} am4_exe=${AM4_GFDL_EXE} slurm_partition=serc slurm_time=01:00:00 do_batch=False
    # process inputs:
    #n_args = len(sys.argv)
    args = dict([s.split('=') for s in sys.argv[1:] if '=' in s ])
    #
    # NOTE: trying to pass the parameter `slurm_directives` won't work -- ie it's not easy to pass a list as a parmeter because 1) args will be separated by whitespace. also, unless specially handled, it will try to add a directive callde `directives`, so just don't do it.
    #  (spaces), and then 2) some slurm directives (ie, partition) allow comma-separated inputs. so let's just use the slurm_* kwds. 
#    if 'slurm_directives' in args.keys():
#        # NOTE: this string conversion is now done in AM4py.py as well.
#        sd_vals={s1:s2 for s1,s2 in zip(args['slurm_directives'].split(chr(32))[0:-1:2], args['slurm_directives'].split(chr(32))[1::2])}
#        args['slurm_directives'] = sd_vals
    #
    #print('** DEBUG args: {}'.format(args))
    run_script = Setup_and_run(**args)

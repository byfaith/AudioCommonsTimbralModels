import numpy as np
import soundfile as sf
from scipy.signal import spectrogram

def db2mag(dB):
    mag = 10 ** (dB / 20.0)
    return mag


def timbral_depth(fname, dev_output=False, threshold_db=-60, low_frequency_limit=30, crossover_frequency=200,
                  phase_correction=False):

    """
     This function calculates the apparent Depth of an audio file.
     Currently the function only works on the left channel of multi-channel audio files.

     The function calculates 3 parameters: the spectral centroid of low frequencies, ratio of low-frequency
     to all energy, and the roll-on frequency.

      Spectral centroid:    The spectral centroid is calculated for frequencies between 30 and 200 Hz.  A window
                            size of 4096 is used to obtain higher low-frequency resolution, and a 1024 samples hop
                            size to maintain time resolution.

      Ratio:                Calculates the ratio fo magnitude between 30 to 200 Hz compared with magnitude between
                            30 Hz and Nyquist.

      Roll-on frequency:    This calculates the frequency where 95% of energy lies above this frequency.

      Depth:                The depth is calculated by applying the coefficients obtained from a linear regression
                            model, which are hardcoded into this function.

      :param fname: Audio filename to be analysed, including full file path and extension.
      :return: returns the depth as a float representing the relative depth.
    """
    # import for phase correction
    import scipy.stats

    # use pysoundfile to read audio
    audio_samples, fs = sf.read(fname, always_2d=False)

    audio_samples, fs = sf.read(audio_stimuli_name, always_2d=False)
    num_channels = np.shape(audio_samples)
    if len(num_channels) > 1:
        # crudely check for out of phase signals
        if phase_correction:
            r, pval = scipy.stats.pearsonr(audio_samples[:, 0], audio_samples[:, 1])
            if r < -0.5:
                audio_samples = audio_samples[:, 0]  + (audio_samples[:, 1] * -1.0)
            else:
                audio_samples = np.sum(audio_samples, axis=1)

        else:
            audio_samples = np.sum(audio_samples, axis=1)

    # normalise audio
    audio_samples *= (1.0 / max(abs(audio_samples)))

    # set FFT parameters
    nfft = 4096
    hop_size = 3 * nfft / 4
    # get spectrogram
    freq, time, spec = spectrogram(audio_samples, fs, 'hamming', nfft,
                                   hop_size, nfft, 'constant', True, 'spectrum')

    # get the index for the low-frequency limit, 30 Hz
    low_limit_idx = np.argmax(freq >= low_frequency_limit)

    # get the index for the cross-over frequency, 200 Hz
    crossover_idx = np.argmax(freq >= crossover_frequency)

    # set threshold for ignoring time segments with no noise, selected from the training stimuli
    threshold = db2mag(threshold_db) # 0.005 ** 2


    # define arrays for storing metrics
    all_lower_centroid = []
    all_thx_lower_centroid = []
    all_lower_ratio = []
    all_thx_lower_ratio = []
    all_rollon = []
    all_thx_rollon = []
    all_lowpower = []
    all_thx_lowpower = []
    all_tpower = []


    # get metrics for each time segment of the spectrogram
    for idx in range(1, len(time)):
        current_spectrum = spec[low_limit_idx:, idx]
        tpower = np.sum(current_spectrum)
        all_tpower.append(tpower)

        # estimate if time segment contains audio energy or just noise
        if tpower > threshold:
            # calculate the spectral centroid and ratio
            lower_spectrum = spec[low_limit_idx:crossover_idx, idx]
            lower_fls = freq[low_limit_idx:crossover_idx]
            lower_power = np.sum(lower_spectrum)
            all_thx_lowpower.append(lower_power)
            all_lowpower.append(lower_power)


            lower_centroid = np.sum(lower_spectrum * lower_fls) / float(lower_power)
            lower_ratio = lower_power / float(tpower)

            # calculate the roll-on frequency
            cumulative_spectral_power = current_spectrum[0]
            counter = 0
            rollon_threshold = tpower * 0.05
            while cumulative_spectral_power < rollon_threshold:
                counter += 1
                cumulative_spectral_power = np.sum(current_spectrum[:counter])

            rollon = freq[counter + low_limit_idx]

            all_lower_centroid.append(lower_centroid)
            all_thx_lower_centroid.append(lower_centroid)
            all_lower_ratio.append(lower_ratio)
            all_thx_lower_ratio.append(lower_ratio)
            all_rollon.append(rollon)
            all_thx_rollon.append(rollon)

            # print all_lower_centroid

        else:
            all_lower_centroid.append(0)
            all_lower_ratio.append(0)
            all_rollon.append(0)
            all_thx_lowpower.append(0)

            lower_spectrum = spec[low_limit_idx:crossover_idx, idx]
            lower_power = np.sum(lower_spectrum)
            all_lowpower.append(lower_power)


    # get mean values
    mean_lower_centroid = np.mean(all_lower_centroid)
    mean_lower_ratio = np.mean(all_lower_ratio)
    mean_rollon = np.mean(all_rollon)
    mean_lowpower = np.mean(all_lowpower)
    mean_thx_lower_centroid = np.mean(all_thx_lower_centroid)
    mean_thx_lower_ratio = np.mean(all_thx_lower_ratio)
    mean_thx_rollon = np.mean(all_thx_rollon)
    mean_thx_lowpower = np.mean(all_thx_lowpower)
    weighted_mean_lower_centroid = np.average(all_lower_centroid, weights=all_tpower)
    weighted_mean_lower_ratio = np.average(all_lower_ratio, weights=all_tpower)
    weighted_mean_rollon = np.average(all_rollon, weights=all_tpower)
    weighted_mean_lowpower = np.average(all_lowpower, weights=all_tpower)


    '''
     Perform linear regression to obtain depth
    '''
    # coefficients from linear regression
    coefficients = np.array([-0.0370864447684, 152.569714872, -0.0577703172507, -1.83339263537, 0.000716827172454,
                             -0.156630837052, 0.0133395675543, 10.8565562292])

    # pack metrics into a matrix
    all_metrics = np.zeros(8)

    all_metrics[0] = mean_lower_centroid
    all_metrics[1] = mean_lower_ratio
    all_metrics[2] = mean_rollon
    all_metrics[3] = np.array(mean_lower_centroid) * np.array(mean_lower_ratio)
    all_metrics[4] = np.array(mean_lower_centroid) * np.array(mean_rollon)
    all_metrics[5] = np.array(mean_lower_ratio) * np.array(mean_rollon)
    all_metrics[6] = np.array(mean_lower_centroid) * np.array(mean_lower_ratio) * np.array(mean_rollon)
    all_metrics[7] = 1.0

    # perform linear regression
    depth = np.sum(all_metrics * coefficients)

    # this return is maintained for testing in the future
    if dev_output:
        return mean_lower_centroid, mean_lower_ratio, mean_rollon, \
               mean_thx_lower_centroid, mean_thx_lower_ratio, mean_thx_rollon, \
               weighted_mean_lower_centroid, weighted_mean_lower_ratio, weighted_mean_rollon, \
               mean_lowpower, mean_thx_lowpower, weighted_mean_lowpower

        # mean_lower_centroid, mean_lower_ratio, mean_rollon, depth
    else:
        return depth


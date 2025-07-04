import matplotlib.pyplot as plt

def show_results(results):
    df = results
    fig, axs = plt.subplots(nrows=3, ncols=1, figsize=(12, 8), sharex=True)

    axs[0].plot(df.index, df['p_mp'], label='P_mp')
    axs[0].set_ylabel('Power [W]')
    axs[0].legend()

    axs[1].plot(df.index, df['v_mp'], label='V_mp', color='orange')
    axs[1].set_ylabel('Voltage [V]')
    axs[1].legend()

    axs[2].plot(df.index, df['i_mp'], label='I_mp', color='green')
    axs[2].set_ylabel('Current [A]')
    axs[2].legend()

    plt.xlabel('Time')
    plt.suptitle('PV Parameters Over Time')
    plt.tight_layout()
    plt.show()
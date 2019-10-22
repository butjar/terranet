def chan_to_freq(chan, five_ghz_band=True):
    if five_ghz_band:
        return 5000 + (5 * chan)
    else:
        return 2407 + (5 * chan)


def freq_to_chan(freq, five_ghz_band=True):
    if five_ghz_band:
        return (freq - 5000) // 5
    else:
        return (freq - 2407) // 5


def chan_to_tuple(chan, five_ghz_band=True):
    if five_ghz_band:
        if chan > 128 or chan < 100:
            raise ValueError('Channel number must be in range [100, 128].')

        if chan % 2 != 0:
            raise ValueError('Uneven channel numbers are not allowed in the supported range!')

        freq = chan_to_freq(chan, five_ghz_band=True)
        start_freq = 5490

        dist = freq - start_freq

        if dist % 80 == 0:
            width = 8
        elif dist % 40 == 0:
            width = 4
        elif dist % 20 == 0:
            width = 2
        elif dist % 10 == 0:
            width = 1
        else:
            raise RuntimeError('This should not happen!')

        min_chan = (freq_to_chan(freq - ((20 * width) // 2) + 10) - 100) // 4
        max_chan = (freq_to_chan(freq + ((20 * width) // 2) - 10) - 100) // 4

        return min_chan, max_chan
    else:
        raise NotImplementedError()


def valid_5ghz_outdoor_channels():
    for i in range(100, 129, 2):
        yield chan_to_tuple(i)


def tuple_to_chan(chan, five_ghz_band=True):
    if chan[1] < chan[0]:
        raise ValueError('Max Channel must be greater than or equal to min Channel!')

    if five_ghz_band:
        width = (chan[1] - chan[0] + 1) * 20

        if width not in [20, 40, 80, 160]:
            raise ValueError('Invalid channel width!')

        lower_freq = chan_to_freq(100 + (chan[0] * 4)) - 10
        center_freq = lower_freq + (width // 2)

        start_freq = 5490
        if (center_freq - start_freq - (width // 2)) % width != 0:
            raise ValueError('Unaligned channels are not permitted!')

        return freq_to_chan(center_freq)
    else:
        raise NotImplementedError()


if __name__ == '__main__':
    print 100, chan_to_tuple(100)
    print 124, chan_to_tuple(124)
    print 106, chan_to_tuple(106)
    print '0, 0', tuple_to_chan((0, 0))
    print '0, 7', tuple_to_chan((0, 7))
    print '1, 1', tuple_to_chan((1, 1))
    print '7, 7', tuple_to_chan((7, 7))
    print '6, 7', tuple_to_chan((6, 7))
    print '4, 7', tuple_to_chan((4, 7))

    for x, y in valid_5ghz_outdoor_channels():
        print x, y, tuple_to_chan((x, y))

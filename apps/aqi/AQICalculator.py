class AQICalculator:
    @staticmethod
    def PM25(value):

        v = round(value, 1)
        breakpoints = [
            (0, 50, 0.0, 12.0),
            (51, 100, 12.1, 35.4),
            (101, 150, 35.5, 55.4),
            (151, 200, 55.5, 150.4),
            (201, 300, 150.5, 250.4),
            (301, 400, 250.5, 350.4),
            (401, 500, 350.5, 500.4),
        ]

        aqi = 0
        for i_low, i_high, c_low, c_high in breakpoints:
            if c_low <= v <= c_high:
                aqi = ((i_high - i_low) / (c_high - c_low)) * (v - c_low) + i_low
            elif v >= 500.5:
                aqi = 500

        return int(aqi)

    @staticmethod
    def PM10(v):

        value = round(v)

        aqi = 0

        if 0 <= value < 54:
            aqi = 0.9259 * value
        elif 54 <= value < 155:
            aqi = (0.4949 * value) + 23.778
        elif 155 <= value < 255:

            aqi = (0.4949 * value) + 24.283
        elif 255 <= value < 355:

            aqi = (0.4949 * value) + 24.788
        elif 355 <= value < 425:

            aqi = (1.4348 * value) - 308.35
        elif 425 <= value < 505:

            aqi = (1.2532 * value) - 231.59
        elif 505 <= value <= 604:

            aqi = value - 104
        else:

            aqi = 500

        return int(aqi)

    @staticmethod
    def NO2(value):

        value = value / 1000
        aqi = 0
        aqi_text = ""

        if 0 <= value < 0.054:
            aqi_text = "سالم"
            aqi = 943.4 * value
        elif 0.054 <= value < 0.101:
            aqi_text = "قابل قبول"
            aqi = (1065.2 * value) - 6.5217
        elif 0.101 <= value < 0.361:
            aqi_text = "ناسالم برای گروه های حساس"
            aqi = (189.19 * value) + 81.892
        elif 0.361 <= value < 0.65:
            aqi_text = "ناسالم"
            aqi = (175.63 * value) + 87.599
        elif 0.65 <= value < 1.25:
            aqi_text = "خیلی ناسالم"
            aqi = (167.8 * value) + 91.932
        elif 1.25 <= value < 1.65:
            aqi_text = "خطرناک"
            aqi = (253.85 * value) - 16.308
        elif 1.65 <= value <= 2.04:
            aqi_text = "خیلی خطرناک"
            aqi = (253.85 * value) - 17.846
        else:
            aqi_text = "خیلی خطرناک"
            aqi = 500

        return int(aqi)

    @staticmethod
    def SO2(value):

        value = value / 1000
        aqi = 0
        aqi_text = ""

        if 0 <= value < 0.035:
            aqi_text = "سالم"
            aqi = 1470.6 * value
        elif 0.035 <= value < 0.145:
            aqi_text = "قابل قبول"
            aqi = (449.54 * value) + 35.266
        elif 0.145 <= value < 0.225:
            aqi_text = "ناسالم برای گروه های حساس"
            aqi = (620.25 * value) + 11.063
        elif 0.225 <= value < 0.305:
            aqi_text = "ناسالم"
            aqi = (620.25 * value) + 11.443
        elif 0.305 <= value < 0.605:
            aqi_text = "خیلی ناسالم"
            aqi = (331.1 * value) + 100.01
        elif 0.605 <= value < 0.805:
            aqi_text = "خطرناک"
            aqi = (497.49 * value) + 0.0201
        elif 0.805 <= value <= 1.004:
            aqi_text = "خیلی خطرناک"
            aqi = (497.49 * value) + 0.5226
        else:
            aqi_text = "خیلی خطرناک"
            aqi = 500

        return int(aqi)

    @staticmethod
    def CO(value):
        value = value / 1000

        aqi = 0
        aqi_text = ""

        if 0 <= value < 4.5:
            aqi_text = "سالم"
            aqi = 11.364 * value
        elif 4.5 <= value < 9.5:
            aqi_text = "قابل قبول"
            aqi = (10 * value) + 6
        elif 9.5 <= value < 12.5:
            aqi_text = "ناسالم برای گروه های حساس"
            aqi = (16.897 * value) - 59.517
        elif 12.5 <= value < 15.5:
            aqi_text = "ناسالم"
            aqi = (16.897 * value) - 60.207
        elif 15.5 <= value < 30.5:
            aqi_text = "خیلی ناسالم"
            aqi = (6.6443 * value) + 98.013
        elif 30.5 <= value < 40.5:
            aqi_text = "خطرناک"
            aqi = (10 * value) - 4
        elif 40.5 <= value <= 50.4:
            aqi_text = "خیلی خطرناک"
            aqi = (10 * value) - 4
        else:
            aqi_text = "خیلی خطرناک"
            aqi = 500

        return int(aqi)

    @staticmethod
    def O3(value):

        value = value / 1000
        aqi = 0
        aqi_text = ""

        if 0 <= value < 0.0626:
            aqi_text = "سالم"
            aqi = 800 * value
        elif 0.0626 <= value < 0.125:
            aqi_text = "قابل قبول"
            aqi = (796.75 * value) + 1.2033
        elif 0.125 <= value < 0.165:
            aqi_text = "ناسالم برای گروه های حساس"
            aqi = (1225 * value) - 50.9
        elif 0.165 <= value < 0.205:
            aqi_text = "ناسالم"
            aqi = (1256.4 * value) - 56.308
        elif 0.205 <= value < 0.405:
            aqi_text = "خیلی ناسالم"
            aqi = (497.49 * value) + 99.015
        elif 0.405 <= value < 0.505:
            aqi_text = "خطرناک"
            aqi = (1000 * value) - 104
        elif 0.505 <= value <= 0.604:
            aqi_text = "خیلی خطرناک"
            aqi = (1000 * value) - 104
        else:
            aqi_text = "خیلی خطرناک"
            aqi = 500

        return int(aqi)

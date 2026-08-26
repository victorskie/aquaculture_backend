function is_safe = evaluate_water(temp, ph, turb, temp_delta, ph_delta, turb_delta)
    % Auto-generated ML Decision Tree Logic

    if turb <= 22.3850
        if ph_delta <= -0.4850
            is_safe = 0;
        else
            if ph_delta <= 0.4950
                if temp <= 25.0000
                    is_safe = 0;
                else
                    if temp <= 29.9350
                        if ph <= 6.4250
                            is_safe = 0;
                        else
                            if ph <= 8.5350
                                if temp_delta <= 2.0100
                                    if temp_delta <= -2.0350
                                        is_safe = 0;
                                    else
                                        if turb_delta <= 15.2500
                                            is_safe = 1;
                                        else
                                            is_safe = 0;
                                        end
                                    end
                                else
                                    is_safe = 0;
                                end
                            else
                                is_safe = 0;
                            end
                        end
                    else
                        if temp <= 32.0400
                            if temp <= 32.0000
                                if ph_delta <= 0.0950
                                    if ph <= 8.4650
                                        if ph <= 6.5400
                                            is_safe = 0;
                                        else
                                            if temp_delta <= 1.8950
                                                if temp_delta <= -2.0050
                                                    is_safe = 0;
                                                else
                                                    is_safe = 1;
                                                end
                                            else
                                                is_safe = 0;
                                            end
                                        end
                                    else
                                        is_safe = 0;
                                    end
                                else
                                    if turb <= 17.5250
                                        is_safe = 0;
                                    else
                                        if turb <= 17.8650
                                            is_safe = 1;
                                        else
                                            is_safe = 0;
                                        end
                                    end
                                end
                            else
                                if temp_delta <= -1.4350
                                    is_safe = 0;
                                else
                                    is_safe = 1;
                                end
                            end
                        else
                            is_safe = 0;
                        end
                    end
                end
            else
                is_safe = 0;
            end
        end
    else
        is_safe = 0;
    end
end

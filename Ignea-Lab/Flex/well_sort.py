def group_wells(unique_wells):
    # Sort wells in ascending order
    unique_wells.sort(key=lambda x: (ord(x[0]) - 65, int(x[1:])))

    grouped_wells = []
    
    for well in unique_wells:
        if not grouped_wells:
            grouped_wells.append([well])
        else:
            last_group = grouped_wells[-1]
            last_well = last_group[-1]
            
            # Check if the current well is vertically adjacent to the last well in the last group
            if ord(well[0]) - ord(last_well[0]) == 1 and int(well[1:]) == int(last_well[1:]):
                last_group.append(well)
            else:
                grouped_wells.append([well])

    return grouped_wells

# Example list of unique wells
unique_wells = ['A1', 'A2', 'A4', 'B3', 'C5', 'C6', 'D11', 'H12']

result = group_wells(unique_wells)
for group in result:
    print(group)
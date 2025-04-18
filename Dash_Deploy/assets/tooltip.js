window.dccFunctions = window.dccFunctions || {};

window.dccFunctions.getSundayByNBAWeek = function(nbaWeek) {
    const csvData = `
sunday,nba_week
2024-06-23,-16
2024-06-30,-15
2024-07-07,-14
2024-07-14,-13
2024-07-21,-12
2024-07-28,-11
2024-08-04,-10
2024-08-11,-9
2024-08-18,-8
2024-08-25,-7
2024-09-01,-6
2024-09-08,-5
2024-09-15,-4
2024-09-22,-3
2024-09-29,-2
2024-10-06,-1
2024-10-13,0
2024-10-20,1
2024-10-27,2
2024-11-03,3
2024-11-10,4
2024-11-17,5
2024-11-24,6
2024-12-01,7
2024-12-08,8
2024-12-15,9
2024-12-22,10
2024-12-29,11
2025-01-05,12
2025-01-12,13
2025-01-19,14
2025-01-26,15
2025-02-02,16
2025-02-09,17
2025-02-16,18
2025-02-23,19
2025-03-02,20
2025-03-09,21
2025-03-16,22
2025-03-23,23
2025-03-30,24
2025-04-06,25
2025-04-13,26
2025-04-20,27
2025-04-27,28
2025-05-04,29
2025-05-11,30
`;

    const rows = csvData.trim().split('\n').slice(1);
    const data = rows.map(row => {
        const [sunday, nbaWeek] = row.split(',');
        return { sunday, nbaWeek: parseInt(nbaWeek, 10) };
    });

    const match = data.find(row => row.nbaWeek === nbaWeek);

    if (match) {
        // Parse date manually to avoid timezone issues
        const [year, month, day] = match.sunday.split('-').map(Number);
        const date = new Date();
        date.setFullYear(year, month - 1, day); // month is 0-based

        const dayOfMonth = date.getDate();

        const monthAbbreviations = [
            'Jan.', 'Feb.', 'Mar.', 'Apr.', 'May.', 'Jun.',
            'Jul.', 'Aug.', 'Sep.', 'Oct.', 'Nov.', 'Dec.'
        ];
        const monthAbbr = monthAbbreviations[date.getMonth()];

        return `${monthAbbr} ${dayOfMonth}`;
    } else {
        throw new Error(`No Sunday found for NBA Week ${nbaWeek}`);
    }
};

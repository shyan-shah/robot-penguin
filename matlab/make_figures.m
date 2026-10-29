function make_figures()
%MAKE_FIGURES  Turn the search logs into figures for the report.
%
% Reads the JSON the Python searches write and draws:
%   1  gait search convergence, and what the score was actually buying
%   2  the before/after that matters - ground clearance
%   3  how each gait does on carpet
%   4  the learning curve
%
% Everything is measured; nothing here is illustrative.

    here = fileparts(mfilename('fullpath'));
    tuned = fullfile(fileparts(here), 'sim', 'tuned');
    outd = fullfile(here, 'out');
    if ~isfolder(outd), mkdir(outd); end

    %% ---------------------------------------------------- 1. convergence
    f = fullfile(tuned, 'gait_v2_hipx22.json');
    if isfile(f)
        d = jsondecode(fileread(f));
        h = d.history;
        it = arrayfun(@(s) s.iter, h);
        best = arrayfun(@(s) s.best, h);
        clr = arrayfun(@(s) s.clear, h);
        spd = arrayfun(@(s) s.speed, h);

        figure('Color','w','Position',[80 80 1120 420]);
        subplot(1,2,1);
        plot(it, best, '-o', 'LineWidth', 2); grid on;
        xlabel('CEM iteration'); ylabel('best score');
        title('Cross-entropy search converging');

        subplot(1,2,2); hold on; grid on;
        yyaxis left;  plot(it, clr, '-o','LineWidth',2); ylabel('ground clearance (mm)');
        yline(11,'k--','scuff / step boundary');
        yyaxis right; plot(it, spd, '-s','LineWidth',2); ylabel('forward speed (mm/s)');
        xlabel('CEM iteration');
        title('What the search was actually buying');
        exportgraphics(gcf, fullfile(outd,'gait_convergence.png'), 'Resolution', 150);
        fprintf('wrote gait_convergence.png\n');
    end

    %% ------------------------------------------------ 2. clearance story
    figure('Color','w','Position',[80 80 820 440]);
    names = {sprintf('v1\nmaximise distance'), sprintf('v2\n+ clearance in the score'), ...
             sprintf('geometry limit\n(stance x sin 25 deg)')};
    vals  = [4.4, 17.9, 2*26*sind(25)];
    b = bar(vals, 0.55, 'FaceColor','flat');
    b.CData = [0.85 0.33 0.26; 0.20 0.55 0.35; 0.65 0.65 0.68];
    set(gca,'XTickLabel',names); grid on; ylabel('ground clearance (mm)');
    yline(11,'k--','scuff boundary','LineWidth',1.2);
    for k = 1:numel(vals)
        text(k, vals(k)+0.8, sprintf('%.1f mm', vals(k)), ...
             'HorizontalAlignment','center','FontWeight','bold');
    end
    title({'The same optimiser, the same robot, a different question', ...
           'v1 scuffed the feet along the floor at 4.4 mm'});
    exportgraphics(gcf, fullfile(outd,'clearance.png'), 'Resolution', 150);
    fprintf('wrote clearance.png\n');

    %% ----------------------------------------------------- 3. on carpet
    f = fullfile(tuned, 'terrain.json');
    if isfile(f)
        t = jsondecode(fileread(f));
        surfaces = unique({t.surface}, 'stable');
        v1 = zeros(1,numel(surfaces)); v2 = v1; f1 = v1; f2 = v1;
        for k = 1:numel(surfaces)
            for j = 1:numel(t)
                if strcmp(t(j).surface, surfaces{k})
                    if strcmp(t(j).gait,'v1'), v1(k)=t(j).speed_mms; f1(k)=t(j).falls;
                    else,                      v2(k)=t(j).speed_mms; f2(k)=t(j).falls; end
                end
            end
        end
        figure('Color','w','Position',[80 80 980 440]);
        bar([v1; v2]'); grid on;
        set(gca,'XTickLabel', surfaces); xtickangle(15);
        ylabel('forward speed (mm/s)'); legend({'v1 scuff','v2 clearance'},'Location','best');
        title('Walking speed by surface (negative = went backwards or fell)');
        exportgraphics(gcf, fullfile(outd,'terrain.png'), 'Resolution', 150);
        fprintf('wrote terrain.png\n');
    end

    %% -------------------------------------------------- 4. learning curve
    f = fullfile(tuned, 'learning_curve.json');
    if isfile(f)
        L = jsondecode(fileread(f));
        day = arrayfun(@(s) s.day, L);
        cov = arrayfun(@(s) 100*s.offline/max(1,s.asked), L);
        prec = arrayfun(@(s) 100*s.correct/max(1,s.offline), L);
        items = arrayfun(@(s) s.items, L);
        figure('Color','w','Position',[80 80 1040 420]);
        subplot(1,2,1); hold on; grid on;
        plot(day, movmean(cov,5), 'LineWidth',2);
        plot(day, movmean(prec,5), 'LineWidth',2);
        xlabel('day'); ylabel('%'); ylim([0 105]);
        legend({'answered offline','precision'},'Location','southeast');
        title('What the penguin learns, over four weeks');
        subplot(1,2,2);
        plot(day, items, 'LineWidth',2); grid on;
        xlabel('day'); ylabel('associations stored');
        title('Memory size (384 max, ~17 KB of flash)');
        exportgraphics(gcf, fullfile(outd,'learning.png'), 'Resolution', 150);
        fprintf('wrote learning.png\n');
    end

    fprintf('\nfigures in %s\n', outd);
end

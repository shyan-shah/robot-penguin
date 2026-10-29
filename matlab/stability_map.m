function stability_map()
%STABILITY_MAP  The walking problem for this penguin, in one figure.
%
% The mechanism has no joint that lifts a foot. A foot only leaves the floor
% because the body rolls over the other one, so ground clearance and tip-over
% risk are the same variable seen from two sides:
%
%     clearance = stance * sin(lean)
%     tip-over  when the centre of mass crosses the outer edge of the support foot
%
% This draws both as a function of body lean and stance width, marks where the
% CAD currently sits, and shows what widening the stance would buy. Everything
% here is closed form - it is the sanity check on the physics simulation, not a
% replacement for it.
%
% Geometry from the CAD (CAD/REPORT.md):
%   ankle axis   22 mm outboard of centreline, 24 mm above the floor
%   CoM          105 mm above the floor, on the centreline
%   foot         38 mm wide, inner edge 3 mm from the centreline

    hip_x      = 26;        % mm, half the stance (widened from 22 - see BUILD_LOG)
    com_h      = 105;       % mm above floor
    ankle_h    = 24;        % mm above floor
    foot_w     = 38;        % mm
    foot_inner = 3;         % mm from centreline

    lean = linspace(0, 35, 400);

    % --- clearance of the swing foot -------------------------------------
    stances = [22 26 35];
    figure('Color','w','Position',[80 80 1180 460], 'Theme','light');

    subplot(1,2,1); hold on; grid on; box on;
    cols = lines(numel(stances));
    for k = 1:numel(stances)
        s = stances(k);
        plot(lean, 2*s.*sind(lean), 'LineWidth', 2, 'Color', cols(k,:), ...
             'DisplayName', sprintf('stance \\pm%d mm', s));
    end
    yline(11, 'k--', 'scuff / step boundary', 'LabelHorizontalAlignment','left', ...
          'HandleVisibility','off');
    yline(17.9, ':', 'Color',[0 .5 0], 'LineWidth',1.5, ...
          'Label','achieved in sim (17.9 mm)','LabelHorizontalAlignment','left', ...
          'HandleVisibility','off');
    xlabel('body lean (deg)'); ylabel('swing-foot clearance (mm)');
    title('Clearance comes only from leaning');
    legend('Location','northwest'); xlim([0 35]); ylim([0 45]);

    % --- tip-over ---------------------------------------------------------
    % Body rotates about the grounded ankle axis; CoM swings on a lever of
    % length R at angle phi0 from vertical. It tips when the CoM passes the
    % outer edge of the support foot.
    subplot(1,2,2); hold on; grid on; box on;
    % The ankle axis sits at the centre of its own foot, so the outer edge is
    % half a foot width outboard of it - not a whole stance plus a foot.
    half_foot = foot_w/2;                 % 19 mm
    for k = 1:numel(stances)
        s = stances(k);
        dz = com_h - ankle_h;
        % body rotates about the left ankle axis at x = -s; rotating the CoM
        % lever (s, dz) by `lean` carries the CoM outboard
        comx = -s + s.*cosd(lean) - dz.*sind(lean);
        outer = -s - half_foot;
        plot(lean, comx, 'LineWidth', 2, 'Color', cols(k,:), ...
             'DisplayName', sprintf('stance \\pm%d mm', s));
        yline(outer, '--', 'Color', cols(k,:), 'HandleVisibility','off');
        % mark the crossing
        idx = find(comx <= outer, 1);
        if ~isempty(idx)
            plot(lean(idx), comx(idx), 'o', 'Color', cols(k,:), ...
                 'MarkerFaceColor', cols(k,:), 'HandleVisibility','off');
            text(lean(idx)+0.4, comx(idx)+4, sprintf('%.1f°', lean(idx)), ...
                 'Color', cols(k,:), 'FontWeight','bold');
        end
    end
    ylim([-60 2]); xlabel('body lean (deg)'); ylabel('CoM x (mm), leaning left');
    title('Tip-over: CoM crossing the outer edge (dashed)');
    legend('Location','southwest'); xlim([0 35]);

    exportgraphics(gcf, fullfile(fileparts(mfilename('fullpath')), ...
                   'out', 'stability_map.png'), 'Resolution', 150);

    % --- numbers for the report -------------------------------------------
    fprintf('\n stance   tip-over   usable lean   clearance there\n');
    dz = com_h - ankle_h;
    for s = [22 26 28 32 35]
        f = @(a) s.*cosd(a) - dz.*sind(a) + foot_w/2;
        a = fzero(f, [0 70]);
        usable = a - 6;                   % keep 6 deg of margin
        fprintf(' %+3d mm   %5.1f deg   %6.1f deg     %5.1f mm\n', ...
                s, a, usable, 2*s*sind(usable));
    end
    fprintf(['\n(closed form; the PyBullet model independently gives 28.3 deg ' ...
             'at the \n current %+d mm stance - see sim/tuned/)\n'], hip_x);
end

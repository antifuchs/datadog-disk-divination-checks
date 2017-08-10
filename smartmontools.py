from checks import AgentCheck
import re
from datetime import datetime
import os.path
import subprocess
import string

class SMARTMonTools(AgentCheck):
    def process_sensor(self, line):
        table_sep_re = re.compile('\s*\|\s+')
        table_fields = ['name', 'value', 'unit', 'status']
        return dict(zip(table_fields, table_sep_re.split(line)))

    HEADER_LINE = 'ID# ATTRIBUTE_NAME          FLAG     VALUE WORST THRESH TYPE      UPDATED  WHEN_FAILED RAW_VALUE'

    def safe_device(self, name):
        return string.replace(os.path.basename(name).rsplit('-sas-')[1], '-', '_')

    def check_device(self, device, instance):
        base_tags = [
            'plain_device:'+self.safe_device(device),
            'device:'+device,
            'sensor:smartmontools',
        ]

        if not os.path.exists(device):
            self.service_check('smartmontools.metric_availability', AgentCheck.UNKNOWN, tags=base_tags)
            return
        self.service_check('smartmontools.metric_availability', AgentCheck.OK, tags=base_tags)

        cmd = ['sudo', 'smartctl', '-A', device]
        output = subprocess.check_output(cmd)
        lines = output.splitlines()
        table_regex = re.compile('\s+')
        field_names = [name.lower() for name in table_regex.split(self.HEADER_LINE)]
        readings = [dict(zip(field_names, table_regex.split(line.lstrip(), 10))) for line in lines[lines.index(self.HEADER_LINE):-1]]
        reading_to_metricname = dict()
        reading_to_alert_thresh = dict()
        for gauge in instance['gauges']:
            for smart_name in gauge['smart_names']:
                reading_to_metricname[smart_name] = gauge['metric']
                alert = {}
                if 'warn_past' in gauge:
                    alert['warn'] = gauge['warn_past']
                if 'critical_past' in gauge:
                    alert['critical'] = gauge['critical_past']
                    reading_to_alert_thresh[smart_name] = alert

        for reading in readings:
            if reading['attribute_name'] in reading_to_metricname:
                value = float(reading['raw_value'])
                metric = reading_to_metricname[reading['attribute_name']]
                tags = base_tags + [
                    'name:'+reading['attribute_name'],
                    'type:'+reading['type'],
                    'updated:'+reading['updated'],
                ]
                self.gauge(metric, value, tags=tags)
                if reading['attribute_name'] in reading_to_alert_thresh:
                    thresholds = reading_to_alert_thresh[reading['attribute_name']]
                    check_status = AgentCheck.OK
                    if value > thresholds.get('critical', value):
                        check_status = AgentCheck.CRITICAL
                    if value > thresholds.get('warn', value):
                        check_status = AgentCheck.WARNING

                    self.service_check(metric, check_status, tags=tags)

        return readings

    def check(self, instance):
        for device in instance['devices']:
            self.check_device(device, instance)

if __name__ == '__main__':
    check, instances = SMARTMonTools.from_yaml('/etc/dd-agent/conf.d/smartmontools.yaml')
    for instance in instances:
        print "\nRunning the check against instance: %s" % (instance['host'])
        print check.check(instance)
